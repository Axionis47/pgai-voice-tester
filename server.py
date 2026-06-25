# The real-time bridge server. This is where a live phone call meets Gemini Live.
#
# Twilio places an outbound call and then opens a websocket back to this server's
# /stream endpoint. Over that websocket Twilio sends the caller's audio and plays
# back whatever audio we send it. On the other side we hold one Gemini Live session
# that acts as the patient: it hears the agent's audio and speaks the patient's
# replies.
#
# The /stream handler wires those two sides together. Once a call starts it runs
# two jobs at the same time:
#   1. Phone in  -> convert -> send into Gemini Live   (the agent talking)
#   2. Gemini out -> convert -> send back to the phone (the patient talking)
# When Gemini signals an interruption (the patient barges in), we tell Twilio to
# clear whatever it was still playing so the old reply stops immediately.
#
# Run this with:  python server.py   (it starts uvicorn on port 8080)

import asyncio
import base64
import json
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.audio import TwilioToGeminiConverter, GeminiToTwilioConverter
from src.brain import build_system_instruction, build_live_config
from src.clients import build_gemini_client, load_settings


# Where the project's config files live, found relative to this file so the paths
# work no matter which directory the server is started from.
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SCENARIO_PATH = PROJECT_ROOT / "config" / "scenarios" / "example_scenario.yaml"
KNOWLEDGE_MAP_PATH = PROJECT_ROOT / "config" / "knowledge_map.yaml"

# Gemini Live needs to be told the format of the audio we send in. Twilio audio is
# converted to 16-bit PCM at 16000 Hz before it reaches the session, so this is the
# mime type we stamp on every realtime audio blob.
GEMINI_INPUT_MIME_TYPE = "audio/pcm;rate=16000"


app = FastAPI()


@app.get("/")
def health_check() -> str:
    """Return a tiny health string so you can confirm the server is up.

    What goes in:
        Nothing.

    What comes out:
        A short plain-text message. Visiting http://localhost:8080/ in a browser
        or curling it should return this string.
    """
    return "pgai-voice-tester bridge is running"


def _load_yaml_file(path: Path) -> dict:
    """Read one YAML file from disk and return it as a dictionary.

    What goes in:
        path: the path to a YAML file.

    What comes out:
        The parsed contents as a dictionary. An empty or missing file gives back
        an empty dictionary so callers can always treat the result as a dict.
    """
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as yaml_file:
        loaded = yaml.safe_load(yaml_file)
    if loaded is None:
        return {}
    return loaded


def _build_scenario_from_parameters(custom_parameters: dict) -> dict:
    """Choose the scenario for this call from Twilio's custom parameters.

    Twilio can pass a <Parameter name="scenario" value="..."/> on the stream.
    For this first working bridge we keep it simple: if a "scenario" parameter is
    present and names a file under config/scenarios/, load that file; otherwise
    fall back to the bundled example scenario.

    What goes in:
        custom_parameters: the dictionary Twilio sends under
            start.customParameters (may be empty).

    What comes out:
        A scenario dictionary ready for build_system_instruction.
    """
    scenario_name = custom_parameters.get("scenario")
    if scenario_name:
        candidate_path = PROJECT_ROOT / "config" / "scenarios" / f"{scenario_name}.yaml"
        if candidate_path.exists():
            return _load_yaml_file(candidate_path)

    # No usable parameter, so use the default example scenario.
    return _load_yaml_file(DEFAULT_SCENARIO_PATH)


async def _wait_for_start_event(websocket: WebSocket) -> dict:
    """Read Twilio messages until the "start" event arrives, and return it.

    Twilio first sends a "connected" event, then a "start" event that carries the
    streamSid and any custom parameters. We skip everything until "start" so the
    caller gets exactly the data it needs to open the Gemini session.

    What goes in:
        websocket: the open Twilio media stream websocket.

    What comes out:
        The parsed "start" event as a dictionary. Raises WebSocketDisconnect if
        the socket closes before a start event is seen.
    """
    while True:
        raw_message = await websocket.receive_text()
        message = json.loads(raw_message)
        if message.get("event") == "start":
            return message


async def _pump_phone_audio_into_gemini(
    websocket: WebSocket,
    gemini_session,
    twilio_to_gemini: TwilioToGeminiConverter,
    stop_event: asyncio.Event,
) -> None:
    """Read the agent's audio from Twilio and feed it into the Gemini session.

    This is job 1 of the bridge. It loops over incoming Twilio websocket messages.
    For each "media" event it base64-decodes the mulaw payload, converts it to the
    PCM 16 kHz that Gemini Live expects, and sends it in as realtime audio. When
    Twilio sends "stop" or the socket closes, it sets the shared stop flag so the
    other job knows to wind down too.

    What goes in:
        websocket: the open Twilio media stream websocket.
        gemini_session: the live Gemini session to send audio into.
        twilio_to_gemini: the per-call converter (mulaw 8k -> PCM 16k).
        stop_event: a shared flag set when the call should end.

    What comes out:
        Nothing. Runs until the call ends, then returns.
    """
    from google.genai import types

    try:
        while not stop_event.is_set():
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            event_type = message.get("event")

            if event_type == "media":
                # Twilio sends the audio base64-encoded inside media.payload.
                payload_base64 = message["media"]["payload"]
                mulaw_frame = base64.b64decode(payload_base64)
                pcm_16k = twilio_to_gemini.convert(mulaw_frame)
                await gemini_session.send_realtime_input(
                    audio=types.Blob(
                        data=pcm_16k,
                        mime_type=GEMINI_INPUT_MIME_TYPE,
                    )
                )
            elif event_type == "stop":
                # Twilio told us the call ended. Stop both jobs.
                break
    except WebSocketDisconnect:
        # The caller hung up or the line dropped; treat it as a normal end.
        pass
    finally:
        stop_event.set()


async def _pump_gemini_audio_into_phone(
    websocket: WebSocket,
    gemini_session,
    gemini_to_twilio: GeminiToTwilioConverter,
    stream_sid: str,
    stop_event: asyncio.Event,
) -> None:
    """Read the patient's audio from Gemini and play it back over the phone.

    This is job 2 of the bridge. It loops over messages coming out of the Gemini
    Live session. When Gemini sends spoken audio, it converts that PCM 24 kHz into
    Twilio mulaw 8 kHz 20 ms frames and sends each frame back over the websocket so
    the agent hears the patient. When Gemini signals an interruption (the patient
    barged in over the agent), it tells Twilio to clear its playback queue so the
    cancelled reply stops at once.

    What goes in:
        websocket: the open Twilio media stream websocket.
        gemini_session: the live Gemini session to read audio from.
        gemini_to_twilio: the per-call converter (PCM 24k -> mulaw 8k frames).
        stream_sid: the Twilio stream id, required on every message we send back.
        stop_event: a shared flag set when the call should end.

    What comes out:
        Nothing. Runs until the call ends, then returns.
    """
    try:
        # session.receive() yields one message at a time for the life of the call.
        async for message in gemini_session.receive():
            if stop_event.is_set():
                break

            server_content = message.server_content

            # Interruption: the patient started talking over the agent. Drop any
            # audio we were still holding and tell Twilio to flush its queue.
            if server_content is not None and server_content.interrupted:
                gemini_to_twilio.reset_after_interruption()
                await _send_clear(websocket, stream_sid)
                continue

            # Spoken audio arrives as raw PCM bytes on message.data. Convert it to
            # Twilio frames and send each one back to be played to the agent.
            audio_bytes = message.data
            if audio_bytes:
                twilio_frames = gemini_to_twilio.convert(audio_bytes)
                for frame in twilio_frames:
                    await _send_media(websocket, stream_sid, frame)
    except WebSocketDisconnect:
        # The phone side closed; nothing left to play to.
        pass
    finally:
        stop_event.set()


async def _send_media(websocket: WebSocket, stream_sid: str, mulaw_frame: bytes) -> None:
    """Send one mulaw frame to Twilio to be played to the caller.

    What goes in:
        websocket: the open Twilio media stream websocket.
        stream_sid: the Twilio stream id this audio belongs to.
        mulaw_frame: one 160-byte mulaw frame (20 ms at 8 kHz).

    What comes out:
        Nothing. The frame is base64-encoded and written to the websocket as the
        JSON "media" message shape Twilio expects for outbound audio.
    """
    payload_base64 = base64.b64encode(mulaw_frame).decode("ascii")
    outbound_message = {
        "event": "media",
        "streamSid": stream_sid,
        "media": {"payload": payload_base64},
    }
    await websocket.send_text(json.dumps(outbound_message))


async def _send_clear(websocket: WebSocket, stream_sid: str) -> None:
    """Tell Twilio to flush any audio it has queued but not yet played.

    Used for barge-in: when the patient interrupts, the agent should stop hearing
    the patient's previous, now-cancelled sentence right away.

    What goes in:
        websocket: the open Twilio media stream websocket.
        stream_sid: the Twilio stream id to clear.

    What comes out:
        Nothing. A JSON "clear" message is written to the websocket.
    """
    clear_message = {"event": "clear", "streamSid": stream_sid}
    await websocket.send_text(json.dumps(clear_message))


@app.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    """Bridge one Twilio phone call to one Gemini Live patient session.

    This runs for the whole length of a single call. It accepts the websocket,
    waits for Twilio's start event, opens a Gemini Live session shaped by the
    chosen scenario, then runs the two audio jobs at the same time until the call
    ends from either side.

    What goes in:
        websocket: the incoming Twilio media stream websocket connection.

    What comes out:
        Nothing. The function returns when the call has fully ended and both audio
        jobs have stopped.
    """
    await websocket.accept()

    # Wait for the start event so we know the streamSid and which scenario to run.
    try:
        start_event = await _wait_for_start_event(websocket)
    except WebSocketDisconnect:
        return

    start_details = start_event.get("start", {})
    stream_sid = start_details.get("streamSid", "")
    custom_parameters = start_details.get("customParameters", {})

    # Decide the patient persona for this call and turn it into a Gemini config.
    settings = load_settings()
    scenario = _build_scenario_from_parameters(custom_parameters)
    knowledge_map = _load_yaml_file(KNOWLEDGE_MAP_PATH)
    system_instruction = build_system_instruction(scenario, knowledge_map)
    live_config = build_live_config(settings, system_instruction)

    gemini_client = build_gemini_client()
    live_model = settings.get("models", {}).get("live_model", "gemini-live-2.5-flash")

    # One shared flag both jobs watch so either side ending stops the whole call.
    stop_event = asyncio.Event()

    # Fresh per-call audio converters so resampler state never leaks between calls.
    twilio_to_gemini = TwilioToGeminiConverter()
    gemini_to_twilio = GeminiToTwilioConverter()

    # Open the live session and run both audio jobs until the call ends. The async
    # context manager closes the session cleanly when we leave the block.
    async with gemini_client.aio.live.connect(
        model=live_model, config=live_config
    ) as gemini_session:
        phone_to_gemini_job = asyncio.create_task(
            _pump_phone_audio_into_gemini(
                websocket, gemini_session, twilio_to_gemini, stop_event
            )
        )
        gemini_to_phone_job = asyncio.create_task(
            _pump_gemini_audio_into_phone(
                websocket, gemini_session, gemini_to_twilio, stream_sid, stop_event
            )
        )

        # Wait until the first job finishes (call ended), then make sure the other
        # job stops too and is cleaned up before we close the session.
        await stop_event.wait()
        for job in (phone_to_gemini_job, gemini_to_phone_job):
            job.cancel()
        await asyncio.gather(
            phone_to_gemini_job, gemini_to_phone_job, return_exceptions=True
        )


if __name__ == "__main__":
    # Start the server. host 0.0.0.0 lets the cloudflared tunnel reach it, and
    # port 8080 is the port the tunnel and place_call.py expect.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

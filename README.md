# PGAI Voice Tester

A voice red-teaming bot. It phones a medical receptionist AI, plays a realistic
patient on a live call, records the call on two separate audio channels, and
turns that recording into a clean, speaker-labeled transcript you can read and
judge. Each call follows a scenario defined in a YAML file, so you control who
the patient is and which agent behavior you are testing. Test line:
+1-805-439-8008.

## Architecture

The system has two paths. The LIVE path is the phone call: Twilio dials the
target agent and opens a websocket back to our bridge server (`server.py`). The
bridge holds one Gemini Live session that hears the agent and speaks as the
patient, converting audio between Twilio's phone format and Gemini's format in
both directions at once. The OFFLINE path runs after the call: we download the
dual-channel recording, transcribe each channel on its own with Whisper, decide
which channel is the agent and which is our bot, and merge the two into one
time-ordered transcript.

```
  place_call.py --> Twilio --> AGENT under test
                       |
        Media Streams websocket (mulaw 8 kHz, 20 ms frames)
                       |
                  server.py (the bridge)
             phone -> Gemini  |  Gemini -> phone
                       |
             Gemini Live session = the PATIENT (our bot)

  after the call:
  download_recording.py --> analysis/transcribe.py --> results/transcripts/*.txt
     (dual-channel WAV)        (split, Whisper, merge)     (AGENT / BOT, ordered)
```

For the full detail, file by file and function by function, read
[architecture.md](architecture.md).

## Prerequisites

- Python 3.11 or newer.
- `cloudflared` (the Cloudflare tunnel client), so Twilio can reach your local
  server over a public URL.
- A Google Cloud project with the Vertex AI API enabled, and Application Default
  Credentials set up (run `gcloud auth application-default login`, or point
  `GOOGLE_APPLICATION_CREDENTIALS` at a service account key file).
- A Twilio account with a phone number to dial out from.
- A `.env` file. Copy `.env.example` to `.env` and fill it in. The variables the
  code actually reads are:
  - `GOOGLE_CLOUD_PROJECT`: the GCP project id that hosts the models.
  - `GOOGLE_CLOUD_LOCATION`: the model location. Use `global` (the Gemini Live
    API is served from the global endpoint).
  - `GOOGLE_GENAI_USE_VERTEXAI`: set to `true` to use Vertex AI.
  - `TWILIO_ACCOUNT_SID`: your Twilio account id.
  - `TWILIO_AUTH_TOKEN`: your Twilio auth token.
  - `TWILIO_FROM_NUMBER`: the Twilio number to dial out from.
  - `TARGET_NUMBER`: the agent under test (defaults the `--to` for a call).

## Run it locally

### One command

```
./dev.sh <scenario-name>
```

`dev.sh` does the whole test end to end. It sets up the `.venv` and installs
dependencies, starts the bridge server, opens a cloudflared tunnel, places one
recorded call to the target agent using the chosen scenario, waits for the call
to finish, then downloads and transcribes the recording, and shuts the server
and tunnel down on exit. A scenario name is a file under `config/scenarios/`
without the `.yaml` suffix. With no argument it uses `sample_hours_location`.

### Manual steps

Run the steps yourself when you want more control. Activating the `.venv` first
(`source .venv/bin/activate`) helps.

1. Optional connectivity check:

   ```
   python3 scripts/check_services.py
   ```
2. Start the bridge server. It listens on port 8080.

   ```
   python server.py
   ```
3. Start a public tunnel and copy the host it prints.

   ```
   cloudflared tunnel --url http://localhost:8080
   ```
4. Place a call. Omit `--to` to dial the target agent. `--scenario` is a file
   name under `config/scenarios/` without the `.yaml`.

   ```
   python place_call.py --url <tunnel-host> --scenario <scenario-name>
   ```
5. After the call, download the recording using the call SID printed above.

   ```
   python download_recording.py --sid <callSid>
   ```
6. Transcribe the recording.

   ```
   python analysis/transcribe.py --sid <callSid>
   ```

## Where things land

- Call recordings: `results/recordings/<callSid>.wav` (dual channel, used by the
  transcriber) and `results/recordings/<callSid>.mp3` (mixed mono).
- Clean transcripts: `results/transcripts/<callSid>.txt`, labeled AGENT and BOT
  and ordered by timestamp.

## Findings

The bugs found by the red-team campaign are written up in
[BUG_REPORT.md](BUG_REPORT.md).

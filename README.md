# PGAI Voice Agent Red-Team Tester

An automated voice bot that phones a medical receptionist AI agent, holds a natural
patient conversation, records and transcribes the call, and systematically finds
bugs in the agent's behavior.

Built for the Pretty Good AI engineering challenge. Test line: +1-805-439-8008.

## How it works (short version)

The bot places a real phone call, listens to the agent, decides what a realistic
patient would say next, and speaks back. Each call follows a scenario defined in a
config file. After the call, an offline step transcribes the recording into a clean
labeled transcript. Judging the transcript against what a correct agent should have
done is currently done by hand, with help from an LLM, and the findings are recorded
by hand.

Deeper detail lives in:

- `docs/ARCHITECTURE.md` how the system fits together and what each file does
- `docs/STRATEGY.md` the red-team method and how we plan attacks (generated next)
- `docs/PROBE_PLAYBOOK.md` the library of probes and bugs to test (generated next)
- `CODING_STANDARDS.md` the code rules every subagent follows

## Project layout

```
pgai-voice-tester/
  README.md                project overview
  CODING_STANDARDS.md      the code contract every subagent follows
  requirements.txt         python dependencies
  .env.example             required environment variables (no secrets)
  config/
    settings.yaml          infra, voice, and turn-taking knobs
    knowledge_map.yaml      living intel about the target, grows every call
    scenarios/
      example_scenario.yaml a sample test case (persona, goal, steering, expected)
    personas/              reusable patient personas
  server.py                live bridge: runs the call, converting Twilio audio to and from the Gemini Live session
  src/
    config_loader.py       read the external config files
    clients.py             build the Gemini, Twilio, and Whisper clients
    audio.py               convert audio between Twilio and the Gemini Live session
    brain.py               the patient: build and drive the Gemini Live session
  analysis/
    transcribe.py          offline transcription of the recording (Whisper)
  docs/
    ARCHITECTURE.md        how the system fits together
  results/
    recordings/            saved call audio
    transcripts/           saved transcripts
```

## Stack

- Telephony: Twilio
- Live voice loop: Gemini Live on Vertex AI (model `gemini-live-2.5-flash`, served from the global location). One streaming session hears the agent, decides what the patient says, and speaks the reply.
- Offline transcription: Whisper (faster-whisper), run after the call ends
- Analysis: Gemini

## Setup and run

A test call is a short chain of steps you run by hand.

1. Copy `.env.example` to `.env` and fill it in. Install dependencies from
   `requirements.txt`.
2. Optional connectivity check:

   ```
   python scripts/check_services.py
   ```
3. Start the bridge server. It listens on port 8080.

   ```
   python server.py
   ```
4. Start a public tunnel and copy the host it prints.

   ```
   cloudflared tunnel --url http://localhost:8080
   ```
5. Place a call. Omit `--to` to dial the target agent. `--scenario` takes the
   name of a file under `config/scenarios` without the `.yaml`.

   ```
   python place_call.py --url <tunnel-host> --scenario <scenario-name>
   ```
6. After the call, download the recording using the call SID:

   ```
   python download_recording.py --sid <callSid>
   ```
7. Transcribe the recording:

   ```
   python analysis/transcribe.py --sid <callSid>
   ```

## Status

Skeleton stage. Every file is a documented stub that explains its job. The logic is
filled in next, by subagents, following `CODING_STANDARDS.md`.

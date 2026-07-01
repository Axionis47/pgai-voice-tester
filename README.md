# PGAI Voice Agent Tester Bot

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

- `SUBMISSION.md` the ten curated calls submitted for review, with recordings and transcripts
- `docs/BUG_REPORT.md` the findings: two real bugs plus a caveated design risk
- `docs/ARCHITECTURE.md` how the system fits together and what each file does
- `docs/SCENARIOS.md` how to write a scenario YAML and run a particular one
- `docs/STRATEGY.md` the red-team method and how we plan attacks
- `docs/PROBE_PLAYBOOK.md` the library of probes and bugs to test
- `CODING_STANDARDS.md` the code rules every contributor follows

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

### Quick start

1. Copy `.env.example` to `.env` and fill it in.
2. Run the one command below. It sets up the `.venv`, installs the pinned
   dependencies, starts the bridge server and a cloudflared tunnel, places a
   call to the target agent, waits for the call to finish, downloads and
   transcribes it, prints the transcript path, and shuts everything down.

   ```
   ./dev.sh
   ```

   You can pass a scenario name to run a different test:

   ```
   ./dev.sh sample_hours_location
   ./dev.sh probe_price_multiservice
   ```

   A scenario name is a file under `config/scenarios/` without the `.yaml`
   suffix. With no argument it uses `sample_hours_location`.

### Create your own test

Each test is a scenario YAML in `config/scenarios/`. To make one and place a call
with it:

1. Copy the template:

   ```
   cp config/scenarios/example_scenario.yaml config/scenarios/my_test.yaml
   ```
2. Edit the fields, above all `persona` (who is calling), `goal` (what they want),
   `twist` (the behavior you are testing), and `expected` (what a correct agent
   does, and what counts as a failure).
3. Place the call by the file name without the `.yaml` suffix:

   ```
   ./dev.sh my_test
   ```

See `docs/SCENARIOS.md` for all nine fields and tips for writing a good test.

### Doing it by hand

A test call is a short chain of steps you run by hand. The steps below also
benefit from activating the `.venv` first (`source .venv/bin/activate`).

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

Working. The live bridge places real calls and holds a natural patient
conversation, the offline path produces clean labeled transcripts, and a red-team
campaign of more than thirty recorded calls produced the findings in
`docs/BUG_REPORT.md`. The curated set submitted for review is in `SUBMISSION.md`.

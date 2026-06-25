# PGAI Voice Agent Red-Team Tester

An automated voice bot that phones a medical receptionist AI agent, holds a natural
patient conversation, records and transcribes the call, and systematically finds
bugs in the agent's behavior.

Built for the Pretty Good AI engineering challenge. Test line: +1-805-439-8008.

## How it works (short version)

The bot places a real phone call, listens to the agent, decides what a realistic
patient would say next, and speaks back. Each call follows a scenario defined in a
config file. After the call, an offline step transcribes the recording and checks
the agent's behavior against what a correct agent should have done. Findings are
written to a living knowledge map that shapes the next call.

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
  runner.py                entry point: runs one full test call start to end
  config/
    settings.yaml          infra, voice, and turn-taking knobs
    knowledge_map.yaml      living intel about the target, grows every call
    scenarios/
      example_scenario.yaml a sample test case (persona, goal, steering, expected)
    personas/              reusable patient personas
  src/
    config_loader.py       read the external config files
    clients.py             build the Gemini, Twilio, and Whisper clients
    telephony.py           bridge Twilio call audio to and from the live session
    brain.py               the patient: build and drive the Gemini Live session
    pipeline.py            orchestrate one call until a stop condition is met
    recorder.py            save the call audio
    tracer.py              structured per-call event log
  analysis/
    transcribe.py          offline transcription of the recording (Whisper)
    analyzer.py            compare the call against expected behavior, find bugs
    update_map.py          fold findings into the living knowledge map
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

Copy `.env.example` to `.env` and fill in the keys. Install dependencies from
`requirements.txt`. Then run a single test call:

```
python runner.py --scenario config/scenarios/example_scenario.yaml
```

## Status

Skeleton stage. Every file is a documented stub that explains its job. The logic is
filled in next, by subagents, following `CODING_STANDARDS.md`.

# Architecture

The PGAI Voice Agent Red-Team Tester places a real phone call to a medical
receptionist AI agent, plays a realistic patient, records the conversation, and
uses it to find real, reproducible bugs in the agent. It is built from two halves
that are kept deliberately separate: a fast live half that runs during the call,
and an unhurried offline half that runs after it.

## How it works

**Live half (during the call).** Twilio places the outbound call and streams the
audio over a websocket to a local FastAPI server (`server.py`), which `cloudflared`
exposes to the internet so Twilio can reach it. The server bridges that audio to one
Gemini Live session that plays the patient. The session hears the agent, decides the
patient's next line, and speaks the reply, all in a single streaming loop, so there
is no separate speech-to-text or text-to-speech step. `src/audio.py` converts between
Twilio's call audio and the format Gemini Live expects. Before the call opens,
`src/brain.py` compiles the patient's persona, goal, and steering rules (from the
scenario) plus what we already know about the target (the knowledge map) into the
session's system instruction. The patient's whole plan is set at that point, and the
live loop then just streams audio both ways until the call ends.

**Offline half (after the call).** `download_recording.py` pulls Twilio's
dual-channel recording, and `analysis/transcribe.py` transcribes each channel
separately with Whisper and merges them into one clean transcript labeled AGENT
versus BOT. Judging that transcript against the scenario's expected behavior is done
by hand, with help from an LLM. There is no automated grader, and the findings are
written by hand. The two halves are split on purpose: it keeps the call cheap and
natural while the slower judging work happens later with no time pressure.

## Key design choices, and why

- **One Gemini Live session, not a speech-to-text then LLM then text-to-speech
  chain.** A single speech-to-speech session keeps latency low and the conversation
  natural, which matters because voice quality is the first thing the challenge
  judges. LangChain is not used, because it is the wrong tool for a real-time speech
  loop.
- **Behavior lives in config, not code.** Each test is a YAML scenario (persona,
  goal, steering, expected behavior). Adding a new test is a data change, not a code
  change, and nothing about the patient is hard coded.
- **Steering is compiled into the system instruction up front.** Because the patient
  is one streaming session, its instructions are built once at session open rather
  than injected mid-call. This keeps the live loop simple and predictable.
- **Dual-channel recording, transcribed per channel.** Recording each side on its own
  channel and running Whisper on each gives a clean AGENT versus BOT transcript, which
  is what makes a bug finding easy to verify and hard to argue with.
- **Judging is manual, on purpose.** Rather than ship a half-built automated analyzer,
  the transcript is judged by hand against each scenario's expected oracle. This keeps
  the system honest about what it actually does.
- **A living knowledge map is the single source of truth about the target.** It holds
  what we have learned about the agent (its hours, its weak spots, how it verifies
  identity), grows after every call, and steers the next probe.

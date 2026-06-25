# Architecture

This document explains how the system fits together and what each file is
responsible for. It is the reference for anyone picking up the project.

## What the system does

It is a caller. It places a real phone call to a medical receptionist AI agent,
behaves like a realistic patient, and records the conversation. After the call it
checks the agent's behavior against what a correct agent should have done, and
records what it learned. The goal is to find real, reproducible bugs in the agent.

## The two halves

The system has a live half and an offline half.

The live half runs during the call and must be fast, so the conversation feels
natural. The offline half runs after the call, has no time pressure, and does the
analysis. Splitting them this way lets us keep the call cheap and natural while
doing the heavy thinking later for free.

## Live data flow (during a call)

The live half is one Gemini Live session that hears, thinks, and speaks in a single
streaming loop. There is no separate speech to text or text to speech step. The
session is given a system instruction built from the scenario, the steering rules,
and the knowledge map, so it knows how to play the patient.

1. `runner.py` loads the scenario and config, then asks `pipeline.py` to run the call.
2. `brain.py` builds the Gemini Live system instruction from the scenario spec, the
   steering rules, and the knowledge map, then opens the live session.
3. `telephony.py` places the Twilio call and bridges audio both ways. It sends the
   agent's incoming audio into the live session and sends the session's generated
   audio back out over the call.
4. The Gemini Live session listens to the agent's audio, decides what the patient
   should say next, and speaks the reply, all inside the one session. Gemini Live
   handles voice activity detection and barge in.
5. `brain.py` may inject mid-call steering into the live session as the call unfolds.
6. `pipeline.py` runs the call until a stop condition is met. We still reason in
   turns for logging, steering, and stop conditions, even though the audio streams
   continuously.
7. `recorder.py` saves the audio. `tracer.py` logs every turn and its timing.

## Offline data flow (after a call)

1. `transcribe.py` turns the saved recording into a clean transcript.
2. `analyzer.py` compares what the agent did against the scenario's expected behavior
   and writes a bug record with a severity.
3. `update_map.py` folds anything new into the living knowledge map, which shapes the
   next call.

## Ownership rules

- The brain is the only part that uses an LLM. Everything else is plain mechanics.
- All behavior comes from config files, not from values hard coded in the logic.
- The knowledge map is the single source of what we know about the target.

## File responsibilities

| File | Responsibility |
|------|----------------|
| `runner.py` | Entry point. Runs one full call from start to end, then the analysis. |
| `src/config_loader.py` | Reads the external config files (settings, scenario, knowledge map). |
| `src/clients.py` | Builds the Gemini, Twilio, and Whisper clients the rest of the system uses. |
| `src/telephony.py` | Places the Twilio call and bridges audio to and from the Gemini Live session. |
| `src/brain.py` | The patient. Builds the Gemini Live system instruction from scenario, steering, and knowledge map, opens the live session, and injects any mid-call steering. The only file that uses an LLM in the live path. |
| `src/pipeline.py` | Orchestrates one call. Starts telephony and the live session, drives the recorder and tracer, and runs until a stop condition. |
| `src/recorder.py` | Saves the call audio as ogg or mp3. |
| `src/tracer.py` | Writes a structured per-call event log of turns and timing. |
| `analysis/transcribe.py` | Offline transcription of a recording using Whisper. |
| `analysis/analyzer.py` | Compares the call against the expected behavior and records bugs. |
| `analysis/update_map.py` | Folds new findings into the living knowledge map. |
| `config/settings.yaml` | Infrastructure, voice, and turn-taking knobs. |
| `config/scenarios/*.yaml` | One test case each: persona, goal, steering, expected behavior. |
| `config/knowledge_map.yaml` | Living intel about the target. Grows every call. |

## Stop conditions

A call ends when any of these happen: the scenario goal is reached, the conversation
dead ends, a maximum number of turns is hit, the agent hangs up, or an error occurs.
This keeps a call from running forever.

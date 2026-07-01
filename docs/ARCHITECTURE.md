# Architecture

## What this is

This project is a voice bot that calls a medical receptionist AI agent, plays a real
patient on the phone, records the call, and uses the recording to find real, repeatable
bugs in the agent. It is built as two halves that are kept apart on purpose: a fast half
that runs during the call, and a slow half that runs after it.

## How it works, at a glance

The live half, during the call:

- Twilio places the call and streams the audio to a small local server (`server.py`).
- `cloudflared` exposes that local server to the internet so Twilio can reach it.
- The server feeds the audio into one Gemini Live session that plays the patient. That
  one session hears the agent, decides what the patient says next, and speaks the reply,
  all in a single stream. There is no separate speech-to-text or text-to-speech step.
- `src/audio.py` converts between Twilio's phone audio and the format Gemini Live wants.
- Before the call starts, `src/brain.py` builds the patient's whole plan (persona, goal,
  steering, and what we already know about the target) into the session's instructions.

The slow half, after the call:

- `download_recording.py` pulls Twilio's recording, which has each speaker on its own
  channel.
- `analysis/transcribe.py` runs Whisper on each channel and merges the two into one clean
  transcript labelled AGENT and BOT.
- We read that transcript and judge it by hand, with help from a model. There is no
  automatic grader.

Keeping the two halves apart keeps the call cheap and natural, while the slower, careful
judging happens later with no time pressure.

## How we got here (the iterations)

The first version was a paper skeleton. I sketched out a lot of separate modules for a
pipeline, recording, tracing, analysis, and a runner, and most of them were empty. It
looked like a real system, but almost none of it ran.

The big change was the voice. The normal way to build a voice bot is a chain: turn speech
into text, send the text to a model, then turn the answer back into speech. But a phone
call is real time, and that chain adds a delay at every step. So I dropped it and used one
Gemini Live session that hears and speaks in a single stream. That is also why I removed
the framework I had started with, and why there is no LangChain here.

After that I kept cutting. Once the real system worked, I deleted the empty modules, so
the repo now only describes what actually runs. What the patient does moved out into
config files, so a new test is a one-file change, not a code change.

## Challenges we faced along the way

Getting a live call right was the hard part, and most of the fixes came from listening to
real calls, not from planning.

- **The call dropped after one reply.** The first live version ended the moment the
  patient finished one sentence, because the session stopped after a single turn. The fix
  was to re-enter the listening loop after every turn, so the conversation keeps going.

- **Barge-in, when the patient talks over the agent.** This is the trickiest part of a
  live call, and it is the bug we walk through in the debugging video. When someone
  interrupts, the reply that is already playing lives in two places, and both have to be
  dropped: the leftover audio held in our own converter, and the audio Twilio has already
  queued up to play. If you clear only one of them, the old reply leaks into the next
  turn, so the fix has to flush both.

- **The bot sounded robotic.** I could hear it repeating the same line word for word. So
  I rewrote its steering to say something once and then react, instead of saying it again
  and again.

- **The agent stalled on a name it did not expect.** The agent guesses your name from the
  caller ID, and it froze whenever the patient gave a different one. So I had the patient
  play along with the guessed name instead of fighting it.

## Key design choices, and why

- **One Gemini Live session, not a speech-to-text then model then text-to-speech chain.**
  It keeps the call fast and the voice natural, which is the first thing the challenge
  judges.
- **What the patient does lives in config, not code.** Each test is a YAML file, so adding
  a test is a data change, not a code change, and nothing about the patient is hard coded.
- **The patient's plan is built once, up front,** into the session's instructions. This
  keeps the live loop simple and predictable.
- **Each speaker is recorded on its own channel and transcribed on its own.** That gives a
  clean AGENT versus BOT transcript, which makes a bug easy to check and hard to argue
  with.
- **Judging is done by hand, on purpose.** A half-built automatic grader would hide what
  the system really does, so we keep it honest and judge the transcript ourselves.
- **One living knowledge map** holds what we have learned about the target agent, grows
  after every call, and steers the next call.

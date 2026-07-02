# Architecture

## What this is

This project is a voice bot that phones a medical receptionist AI agent, plays a realistic
patient, records the call, and uses the recording to find real, reproducible bugs in the
agent. It is built as two halves that are kept apart on purpose: a fast half that runs live
during the call, and a slower half that runs after it.

## How it works, at a glance

The live half, during the call:

- Twilio places the outbound call and streams the audio over a websocket to a small local
  server (`server.py`).
- `cloudflared` exposes that local server so Twilio can reach it.
- The server bridges the audio to one Gemini Live session that plays the patient. That one
  session hears the agent, decides the patient's next line, and speaks it, all in a single
  stream. There is no separate speech-to-text or text-to-speech step.
- `src/audio.py` converts between Twilio's phone audio (8 kHz mu-law) and the format Gemini
  Live uses (16 kHz PCM in, 24 kHz PCM out).
- Before the call starts, `src/brain.py` compiles the patient's whole plan (persona, goal,
  steering, and what we already know about the agent) into the session's system instruction.

The offline half, after the call:

- `download_recording.py` pulls Twilio's recording, which keeps each speaker on its own
  channel.
- `analysis/transcribe.py` runs Whisper on each channel and merges the two into one clean
  transcript labelled AGENT and BOT.
- We judge that transcript by hand, with help from a model. There is no automatic grader.

Keeping the two halves apart keeps the call fast and natural, while the slower, careful
judging happens afterwards with no time pressure.

## Two decisions that shaped everything

**One live session, not a three-stage chain.** A phone call is real time, and voice quality
is the first thing that matters. The usual way to build a voice bot chains three services:
speech to text, then a model, then text to speech. Every hand-off adds delay, and the
delays stack into a pause the caller can hear. So the whole live side is one Gemini Live
session that takes audio in and gives audio out directly, with no text stage in the middle.
That is what keeps the voice natural, and it is why LangChain is not used here: it chains
text steps, not a single real-time audio stream.

**Behaviour is data, not code.** None of the patient's behaviour lives in Python. Each
patient is a small YAML scenario file: persona, goal, the one thing being probed, and
steering rules. That file is compiled into the session's system instruction when the call
opens. So a new patient is a new file, not a code change, which is how one engine ran the
whole call campaign.

## The bridge: keeping one conversation alive

A Gemini Live session hands back one turn at a time. You read from it, it streams the
patient's single reply, and then that read closes at the turn boundary. A phone call is
dozens of turns, so a single read would give one reply and then silence.

The fix is a loop: after each turn ends, the bridge re-opens the read on the same open
session, turn after turn, until the call ends. Because the session is never reconnected,
the model holds the whole conversation's context server-side, and no history is ever
re-sent. Turn ten still has the context of turn one.

## Handling interruptions

This is the hardest part of a live call. The patient's reply is produced faster than the
phone can play it, so at any moment part of the reply has been generated and sent but not
yet spoken. That audio is buffered ahead in two places: a small remainder inside our own
converter (the bytes that did not fill a whole 20 ms frame), and the bulk in Twilio's own
playback queue.

When the patient and the agent talk at the same time, Gemini raises an interrupted signal
and the patient's in-progress reply is abandoned. But stopping the model does nothing to
the audio already sent downstream. Left alone, Twilio keeps playing the abandoned reply over
the top of the new turn. That is worse than noise, because the agent is listening: it treats
the stray audio as something the patient said and answers it, and the call drifts.

So on the interrupt, the bridge clears both buffers at once: it empties the converter's
leftover and sends Twilio a clear event to flush its queue. Clearing only one leaves the
other half playing. The one thing it does not reset is the resampler state, because the
outgoing stream is continuous and resetting it mid-call would cause an audible click. Flush
both buffers, keep the resampler, and the barge-in is clean.

## How we got here (the iterations)

The first version was a paper skeleton: separate modules for a pipeline, recording, tracing,
analysis, and a runner, most of them empty. It looked like a system, but almost none of it
ran. Collapsing the voice into one live session reshaped everything, and once the real
system worked, the empty modules were deleted so the repo describes only what runs. Most of
the hard parts above were found by listening to real calls and refining the approach, not by
planning up front.

## What the testing found

The campaign produced two reproducible bugs in the agent, each proven by the agent
contradicting itself across two separate calls: a cancellation policy it disclaims when
asked plainly but confirms when led, and an appointment date it silently substitutes and
then misreports. The full findings, with severity and evidence, are in `docs/BUG_REPORT.md`.

# Regression tests pinning down what must happen when the patient barges in.
#
# During a call the patient (Gemini) can start talking over the agent. Gemini
# reacts by cancelling its own half-spoken reply and sending a message whose
# server_content.interrupted flag is True. At that moment two clean-up steps
# happen so the cancelled reply does not bleed into the next thing the patient
# says:
#
#   1. Drop the leftover audio inside the converter. GeminiToTwilioConverter keeps
#      a sub-frame tail in _leftover_mulaw between convert() calls. That tail
#      belongs to the reply that was just cancelled, so it is now stale. If we kept
#      it, it would get glued onto the front of the next reply and the agent would
#      hear a click of dead audio. The converter's reset_after_interruption() method
#      empties that tail, and the pump calls it on an interruption.
#
#   2. Tell Twilio to clear its queue. We have already streamed frames of the
#      cancelled reply to Twilio, and Twilio buffers them for playback. Unless we
#      send it {"event": "clear", "streamSid": ...} it keeps playing the cancelled
#      reply to the agent even though Gemini has gone quiet. The clear message
#      carries the streamSid so Twilio knows which stream to flush.
#
# The tests lean on the standard-library unittest module and a couple of
# hand-rolled fakes (a fake websocket and a fake Gemini session) so no live call
# or network is needed.

import asyncio
import json
import os
import sys
import unittest

# Make the repo root importable so "import server" and the src package resolve no
# matter how the tests are launched. This file lives in tests/, so the repo root
# is two levels up.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
from src.audio import GeminiToTwilioConverter


class FakeWebSocket:
    """A stand-in for the Twilio websocket that just records what was sent.

    The real websocket writes JSON strings out to Twilio over the network. A unit
    test only cares about what the pump tried to send, so this fake stores every
    outgoing string in a list the test can read back afterwards.
    """

    def __init__(self):
        # Every string handed to send_text lands here, in order, so a test can look
        # for the "clear" message the barge-in path is meant to send.
        self.sent = []

    async def send_text(self, text):
        """Record one outgoing message instead of putting it on a network."""
        self.sent.append(text)


class FakeServerContent:
    """The server_content slice of a Gemini message, holding the interrupted flag.

    The pump reads server_content.interrupted to decide whether the patient barged
    in. This fake carries just that one boolean.
    """

    def __init__(self, interrupted):
        self.interrupted = interrupted


class FakeMessage:
    """A stand-in for one message coming out of a Gemini Live session.

    The pump reads two things off each message: server_content (which carries the
    interrupted flag, or is None when there is no server content) and data (the raw
    PCM audio bytes, or None when the message has no audio). This fake exposes
    exactly those two attributes so a test can hand the pump a message it controls.
    """

    def __init__(self, interrupted=False, data=None):
        # server_content is None when Gemini sends no server content at all. When it
        # is present it carries the interrupted flag, so model it as a tiny object
        # with a single .interrupted attribute.
        self.server_content = FakeServerContent(interrupted) if interrupted else None
        # Raw PCM bytes for spoken audio, or None when this message is not audio.
        self.data = data


class FakeGeminiSession:
    """A stand-in for a Gemini Live session that yields one scripted turn.

    The real session's receive() is an async generator that yields the messages of
    one model turn and then ends. The pump wraps receive() in an outer loop keyed on
    stop_event and re-enters it for each new turn. To hold the test to a single turn
    this fake sets stop_event once the scripted messages run out, so the pump's outer
    loop sees the flag and stops instead of calling receive() again.
    """

    def __init__(self, stop_event, messages):
        # The shared flag the pump watches. Set once the turn's messages are gone.
        self._stop_event = stop_event
        self._messages = messages

    def receive(self):
        """Return an async generator over the scripted messages for one turn.

        This is used directly as "async for message in session.receive()", so
        receive itself is an ordinary method that returns an async generator.
        """
        return self._yield_messages()

    async def _yield_messages(self):
        """Yield each scripted message, then set stop_event to end the pump."""
        for message in self._messages:
            yield message
        # The turn is over. Setting the stop flag makes the pump's outer
        # "while not stop_event.is_set()" loop exit rather than re-enter receive().
        self._stop_event.set()


def run_pump_for_one_turn(websocket, session, converter, stream_sid, stop_event):
    """Drive the real gemini->phone pump through one scripted turn and return.

    A small helper so each test reads as one line instead of repeating the same
    asyncio.run wiring. It runs the actual server pump, not a copy, so the tests
    exercise the real code path.

    What goes in:
        websocket: the FakeWebSocket recording outbound messages.
        session: the FakeGeminiSession scripting the turn.
        converter: the GeminiToTwilioConverter under test.
        stream_sid: the Twilio stream id the pump should stamp on messages.
        stop_event: the shared flag the fake session sets to end the turn.

    What comes out:
        Nothing. Returns once the pump has processed the scripted turn.
    """
    asyncio.run(
        server._pump_gemini_audio_into_phone(
            websocket, session, converter, stream_sid, stop_event
        )
    )


class BargeInConverterFlushTests(unittest.TestCase):
    """Pin down the drop-the-leftover half of barge-in clean-up."""

    def test_converter_exposes_reset_that_clears_leftover(self):
        """The converter must offer a reset that empties its leftover tail.

        A Gemini chunk rarely divides evenly into 160-byte Twilio frames, so the
        converter parks the odd tail in _leftover_mulaw for next time. When the
        reply that produced that tail is cancelled by a barge-in the tail is stale
        and has to go, otherwise it leads off the front of the next reply. This test
        feeds the converter a chunk that leaves a non-empty tail, then verifies
        reset_after_interruption() empties it.
        """
        converter = GeminiToTwilioConverter()

        # 2000 bytes of 24 kHz PCM. After downsampling and framing this does not
        # land on a clean 160-byte boundary, so a leftover tail is left behind.
        converter.convert(b"\x01\x02" * 1000)
        self.assertNotEqual(
            converter._leftover_mulaw,
            b"",
            "test setup: expected a non-empty leftover before the reset",
        )

        self.assertTrue(
            hasattr(converter, "reset_after_interruption"),
            "the converter must offer a reset_after_interruption method that "
            "drops the stale leftover on a barge-in",
        )
        converter.reset_after_interruption()

        self.assertEqual(
            converter._leftover_mulaw,
            b"",
            "reset_after_interruption must flush the leftover so the cancelled "
            "reply's tail cannot leak into the next utterance",
        )

    def test_pump_flushes_converter_leftover_on_interruption(self):
        """On an interruption the pump must drop the converter's leftover.

        This drives the real pump with a single interrupted message. The converter
        is seeded with a partial frame that stands in for the cancelled reply's
        tail. Once the pump has processed the interruption that tail must be gone.
        """
        converter = GeminiToTwilioConverter()
        # Seed a partial frame directly, as if a cancelled reply left it behind.
        converter._leftover_mulaw = b"\x99\x99\x99"

        stop_event = asyncio.Event()
        websocket = FakeWebSocket()
        session = FakeGeminiSession(stop_event, [FakeMessage(interrupted=True)])

        run_pump_for_one_turn(websocket, session, converter, "MZtest", stop_event)

        self.assertEqual(
            converter._leftover_mulaw,
            b"",
            "the pump must flush the converter leftover on barge-in so stale audio "
            "does not lead off the next reply",
        )


class BargeInTwilioClearTests(unittest.TestCase):
    """Pin down the clear-Twilio's-queue half of barge-in clean-up."""

    def test_pump_sends_clear_with_stream_sid_on_interruption(self):
        """On an interruption the pump must send Twilio a clear for this stream.

        Twilio buffers the outbound frames we already sent, so when Gemini cancels
        its reply the agent keeps hearing it unless we send {"event": "clear",
        "streamSid": ...}. This drives the real pump with a single interrupted
        message and checks the recorded messages for that clear and its streamSid.
        """
        stop_event = asyncio.Event()
        websocket = FakeWebSocket()
        converter = GeminiToTwilioConverter()
        session = FakeGeminiSession(stop_event, [FakeMessage(interrupted=True)])

        run_pump_for_one_turn(websocket, session, converter, "MZtest", stop_event)

        sent_messages = [json.loads(text) for text in websocket.sent]
        clear_messages = [m for m in sent_messages if m.get("event") == "clear"]

        self.assertTrue(
            clear_messages,
            "barge-in must tell Twilio to flush its queued cancelled audio with a "
            "clear event",
        )
        self.assertEqual(
            clear_messages[0].get("streamSid"),
            "MZtest",
            "the clear message must carry the streamSid so Twilio flushes the right "
            "stream",
        )

    def test_pump_does_not_clear_on_a_normal_audio_turn(self):
        """A normal spoken turn with no interruption must not send a clear.

        The clear is destructive: it throws away queued audio. It must fire only on
        a barge-in, never on an ordinary reply, or the patient's own speech would be
        cut off. This drives the pump with a plain audio message (no interruption)
        and asserts no clear was sent. It is the guard rail that stops a later
        change from clearing on every turn.
        """
        stop_event = asyncio.Event()
        websocket = FakeWebSocket()
        converter = GeminiToTwilioConverter()
        # A normal audio message: enough PCM to produce at least one Twilio frame.
        session = FakeGeminiSession(
            stop_event, [FakeMessage(interrupted=False, data=b"\x01\x02" * 1000)]
        )

        run_pump_for_one_turn(websocket, session, converter, "MZtest", stop_event)

        sent_messages = [json.loads(text) for text in websocket.sent]
        clear_messages = [m for m in sent_messages if m.get("event") == "clear"]

        self.assertEqual(
            clear_messages,
            [],
            "no interruption happened, so the pump must not clear Twilio's queue",
        )


if __name__ == "__main__":
    unittest.main()

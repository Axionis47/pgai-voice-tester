# Audio format conversion between Twilio phone audio and Gemini Live audio.
#
# The phone line and the Gemini Live session speak different audio "languages".
# Twilio always uses mulaw (u-law) 8-bit, 8000 Hz, mono. Gemini Live wants to
# HEAR 16-bit PCM at 16000 Hz, and it SPEAKS 16-bit PCM at 24000 Hz. This file is
# the translator that sits in the middle and converts one format to the other in
# both directions.
#
# Resampling (changing the sample rate) needs to remember a little state between
# frames, otherwise you hear clicks at every frame boundary. Because of that, the
# two directions are wrapped in small classes that hold onto that state for the
# whole call. Create one converter per call, then feed it frames one at a time.

import audioop


# Sample rates for each leg of the trip, named so the conversion code reads
# like plain English instead of bare numbers.
TWILIO_SAMPLE_RATE_HZ = 8000        # Twilio phone audio is always 8 kHz.
GEMINI_INPUT_SAMPLE_RATE_HZ = 16000   # Gemini Live expects to hear 16 kHz PCM.
GEMINI_OUTPUT_SAMPLE_RATE_HZ = 24000  # Gemini Live speaks back at 24 kHz PCM.

# All PCM here is signed 16-bit, which is 2 bytes per audio sample. audioop calls
# this the "sample width". Naming it avoids an unexplained "2" scattered around.
PCM_SAMPLE_WIDTH_BYTES = 2

# Audio is mono (one channel) on every leg. ratecv needs to be told this.
CHANNEL_COUNT_MONO = 1

# Twilio plays audio back most smoothly in 20 millisecond chunks. At 8000 Hz
# mulaw that is exactly 160 bytes per chunk (8000 samples/sec * 0.020 sec *
# 1 byte/sample). We slice outgoing audio into pieces of this size.
TWILIO_FRAME_BYTES = 160


class TwilioToGeminiConverter:
    """Turns Twilio mulaw 8 kHz frames into the PCM 16 kHz Gemini Live wants.

    Make one of these per phone call. Each incoming Twilio media frame is mulaw,
    8-bit, 8000 Hz. Gemini Live needs to hear 16-bit PCM at 16000 Hz. This class
    does that conversion and remembers the resampler state across frames so the
    upsampled audio stays smooth from one frame to the next.
    """

    def __init__(self) -> None:
        """Start a fresh converter with no resampler history yet.

        What goes in:
            Nothing.

        What comes out:
            Nothing. The resampler state starts as None, which tells audioop
            this is the first frame. After the first frame it holds the state
            needed to continue smoothly.
        """
        # audioop.ratecv returns a state object on each call that must be passed
        # back in on the next call. None means "this is the very first frame".
        self._resampler_state = None

    def convert(self, mulaw_frame: bytes) -> bytes:
        """Convert one Twilio mulaw frame into Gemini-ready PCM 16 kHz bytes.

        What goes in:
            mulaw_frame: raw mulaw audio bytes from one Twilio media event
                (8-bit, 8000 Hz, mono). Already base64-decoded by the caller.

        What comes out:
            16-bit PCM bytes at 16000 Hz, mono, ready to send into the Gemini
            Live session as realtime audio input.
        """
        # Step 1: mulaw 8-bit -> linear 16-bit PCM, still at 8000 Hz.
        pcm_8k = audioop.ulaw2lin(mulaw_frame, PCM_SAMPLE_WIDTH_BYTES)

        # Step 2: resample 8000 Hz -> 16000 Hz. We pass the saved state in and
        # store the new state so the next frame continues without a click.
        pcm_16k, self._resampler_state = audioop.ratecv(
            pcm_8k,
            PCM_SAMPLE_WIDTH_BYTES,
            CHANNEL_COUNT_MONO,
            TWILIO_SAMPLE_RATE_HZ,
            GEMINI_INPUT_SAMPLE_RATE_HZ,
            self._resampler_state,
        )
        return pcm_16k


class GeminiToTwilioConverter:
    """Turns Gemini PCM 24 kHz audio into Twilio mulaw 8 kHz 20 ms frames.

    Make one of these per phone call. Gemini Live speaks 16-bit PCM at 24000 Hz.
    Twilio needs mulaw, 8-bit, 8000 Hz, and plays back most smoothly in 20 ms
    (160 byte) frames. This class downsamples and converts the audio, remembers
    the resampler state across calls, and also remembers any leftover bytes that
    did not fill a whole 160 byte frame so they lead off the next batch.
    """

    def __init__(self) -> None:
        """Start a fresh converter with no resampler history and no leftovers.

        What goes in:
            Nothing.

        What comes out:
            Nothing. The resampler state starts as None (first chunk) and the
            leftover buffer starts empty.
        """
        # Saved between calls so the 24k -> 8k resample stays smooth.
        self._resampler_state = None

        # Gemini sends audio in chunks of whatever size it likes, so a converted
        # chunk rarely divides evenly into 160 byte Twilio frames. We stash the
        # remainder here and prepend it to the next chunk's output.
        self._leftover_mulaw = b""

    def convert(self, gemini_pcm_chunk: bytes) -> list:
        """Convert one Gemini PCM chunk into a list of Twilio mulaw frames.

        What goes in:
            gemini_pcm_chunk: raw 16-bit PCM bytes at 24000 Hz, mono, as spoken
                by the Gemini Live session.

        What comes out:
            A list of mulaw byte frames, each exactly 160 bytes (20 ms at 8 kHz),
            ready to base64-encode and send to Twilio one at a time. Any bytes
            that do not fill a full 160 byte frame are held back for next time,
            so the list may be empty for a small input chunk.
        """
        # Step 1: resample 24000 Hz -> 8000 Hz, carrying state across calls.
        pcm_8k, self._resampler_state = audioop.ratecv(
            gemini_pcm_chunk,
            PCM_SAMPLE_WIDTH_BYTES,
            CHANNEL_COUNT_MONO,
            GEMINI_OUTPUT_SAMPLE_RATE_HZ,
            TWILIO_SAMPLE_RATE_HZ,
            self._resampler_state,
        )

        # Step 2: linear 16-bit PCM -> mulaw 8-bit, still at 8000 Hz.
        mulaw_8k = audioop.lin2ulaw(pcm_8k, PCM_SAMPLE_WIDTH_BYTES)

        # Step 3: glue any leftover from last time onto the front, then slice the
        # whole thing into exact 160 byte frames. Whatever does not fill a frame
        # becomes the new leftover for next time.
        all_mulaw = self._leftover_mulaw + mulaw_8k
        frames = []
        start = 0
        while start + TWILIO_FRAME_BYTES <= len(all_mulaw):
            frames.append(all_mulaw[start:start + TWILIO_FRAME_BYTES])
            start += TWILIO_FRAME_BYTES
        self._leftover_mulaw = all_mulaw[start:]
        return frames

    def reset_after_interruption(self) -> None:
        """Drop any buffered audio so a barge-in starts cleanly.

        When the patient interrupts (barge-in), Twilio is told to clear its
        playback queue. Any leftover bytes we were holding belong to the old,
        now-cancelled reply, so we throw them away. The resampler state is kept,
        since the 8 kHz output stream itself is continuous.

        What goes in:
            Nothing.

        What comes out:
            Nothing. The leftover buffer is emptied.
        """
        self._leftover_mulaw = b""

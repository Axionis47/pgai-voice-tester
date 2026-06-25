"""Offline transcription of a saved dual-channel call recording.

After a call ends, the live speech to text result is good enough for the bot to
talk in real time, but it is not clean enough to judge what the agent actually
said. This file re-transcribes the saved audio from scratch using faster-whisper,
which is slower but much more accurate.

The recording is a stereo WAV from Twilio's dual-channel recording: each side of
the conversation sits on its own audio channel. We split the two channels, run
the transcriber on each one separately, and then merge the results back into one
timeline. Because each channel holds a single speaker, every channel transcript
is clean and free of cross-talk, which is the whole point of using the WAV
instead of the mixed mono MP3.

The final transcript labels each line as either AGENT (the medical receptionist
AI we are testing) or BOT (our patient bot).
"""

import argparse
import audioop
import sys
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path

# Make the project root importable so "from src.clients import ..." works no
# matter which directory this script is launched from, the same way the other
# runnable scripts in this repo do it.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clients import load_settings, load_whisper_model  # noqa: E402  (import after sys.path setup)


# Speaker labels used throughout the transcript. Kept as named constants so the
# saved file and any downstream code use one consistent spelling.
SPEAKER_AGENT = "AGENT"
SPEAKER_BOT = "BOT"

# The agent answers the phone and opens with a recorded-call disclaimer. We use
# the start of that disclaimer to recognise which channel is the agent. Matching
# is done as a case-insensitive substring so small transcription differences in
# the rest of the sentence do not break the rule.
AGENT_DISCLAIMER_MARKER = "this call may be recorded"


@dataclass
class TranscriptSegment:
    """One chunk of speech from one channel of the recording.

    Attributes:
        speaker: Who is talking. Either SPEAKER_AGENT (the medical receptionist
            AI) or SPEAKER_BOT (our patient bot).
        start_seconds: When this chunk starts, measured from the start of the call.
        end_seconds: When this chunk ends, measured from the start of the call.
        text: The words spoken in this chunk.
    """

    speaker: str
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class Transcript:
    """The full clean transcript of one call, with speakers separated.

    Attributes:
        audio_path: The recording this transcript was made from.
        full_text: The whole call as one labeled, time-ordered block of text.
        segments: The call broken into timed, speaker-labeled chunks, ordered by
            start time.
        language: The detected spoken language, for example "en".
        model_name: The transcription model size that produced this, for the
            record.
    """

    audio_path: str
    full_text: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = ""
    model_name: str = ""


def split_stereo_wav_to_mono_files(wav_path: Path) -> tuple[Path, Path]:
    """Split a stereo WAV into two temporary mono WAV files, one per channel.

    Twilio's dual-channel recording puts each side of the call on its own
    channel. faster-whisper transcribes a single mono stream at a time, so we
    pull each channel out into its own mono WAV file.

    Args:
        wav_path: Path to the stereo (2-channel) WAV recording.

    Returns:
        A tuple (left_channel_path, right_channel_path) pointing at two temporary
        mono WAV files. The caller is responsible for deleting them when done.

    Raises:
        FileNotFoundError: If wav_path does not point to a real file.
        ValueError: If the WAV does not have exactly two channels, since the
            whole point is to separate the two sides of the call.
    """
    if not wav_path.exists():
        raise FileNotFoundError(f"Recording not found at {wav_path}")

    with wave.open(str(wav_path), "rb") as stereo_wav:
        channel_count = stereo_wav.getnchannels()
        sample_width = stereo_wav.getsampwidth()
        frame_rate = stereo_wav.getframerate()
        frames = stereo_wav.readframes(stereo_wav.getnframes())

    if channel_count != 2:
        raise ValueError(
            f"Expected a 2-channel (stereo) WAV so the agent and bot can be "
            f"separated, but {wav_path} has {channel_count} channel(s). Make sure "
            f"the call was recorded with dual-channel recording and the WAV "
            f"(not the mixed mono MP3) was downloaded."
        )

    # audioop.tomono keeps one channel and drops the other. The last two numbers
    # are the weights for the left and right channels: (1, 0) keeps the left
    # channel, (0, 1) keeps the right channel.
    left_channel_frames = audioop.tomono(frames, sample_width, 1, 0)
    right_channel_frames = audioop.tomono(frames, sample_width, 0, 1)

    left_path = _write_mono_wav(left_channel_frames, sample_width, frame_rate)
    right_path = _write_mono_wav(right_channel_frames, sample_width, frame_rate)
    return left_path, right_path


def _write_mono_wav(frames: bytes, sample_width: int, frame_rate: int) -> Path:
    """Write raw mono audio frames to a new temporary WAV file.

    Args:
        frames: Raw mono audio frames (one channel only).
        sample_width: Bytes per sample, copied from the source WAV.
        frame_rate: Samples per second, copied from the source WAV.

    Returns:
        The path to the temporary mono WAV file that was written.
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()

    with wave.open(temp_file.name, "wb") as mono_wav:
        mono_wav.setnchannels(1)
        mono_wav.setsampwidth(sample_width)
        mono_wav.setframerate(frame_rate)
        mono_wav.writeframes(frames)

    return Path(temp_file.name)


def transcribe_one_channel(
    mono_wav_path: Path, transcriber: object
) -> tuple[list[tuple[float, float, str]], str]:
    """Transcribe a single mono channel into timed text segments.

    Args:
        mono_wav_path: Path to a mono WAV holding one speaker's channel.
        transcriber: A loaded faster-whisper model.

    Returns:
        A tuple (segments, language) where segments is a list of
        (start_seconds, end_seconds, text) for each spoken chunk on this channel,
        and language is the detected spoken language, for example "en".
    """
    raw_segments, info = transcriber.transcribe(str(mono_wav_path))

    segments = []
    for segment in raw_segments:
        spoken_text = segment.text.strip()
        if spoken_text:
            segments.append((segment.start, segment.end, spoken_text))

    return segments, info.language


def channel_contains_disclaimer(segments: list[tuple[float, float, str]]) -> bool:
    """Decide whether a channel's transcript contains the agent disclaimer.

    The agent answers the call and opens with a recorded-call disclaimer, so the
    channel that contains it is the agent's channel.

    Args:
        segments: The (start, end, text) segments for one channel.

    Returns:
        True if any segment's text contains the disclaimer marker (matched
        case-insensitively), False otherwise.
    """
    joined_text = " ".join(text for _start, _end, text in segments).lower()
    return AGENT_DISCLAIMER_MARKER in joined_text


def earliest_start_seconds(segments: list[tuple[float, float, str]]) -> float:
    """Return the start time of the first spoken segment on a channel.

    Args:
        segments: The (start, end, text) segments for one channel.

    Returns:
        The earliest start time in seconds, or a very large number if the channel
        has no speech, so a silent channel never wins the "spoke first" test.
    """
    if not segments:
        return float("inf")
    return min(start for start, _end, _text in segments)


def assign_speakers(
    left_segments: list[tuple[float, float, str]],
    right_segments: list[tuple[float, float, str]],
) -> tuple[str, str]:
    """Decide which channel is the agent and which is the bot.

    The rule, in order of preference:
      1. The agent answers the call and opens with a recorded-call disclaimer
         ("This call may be recorded for quality and training purposes"). The
         channel whose transcript contains that disclaimer is the agent; the
         other is the bot. This is the primary, most reliable rule.
      2. If neither channel (or, oddly, both channels) contains the disclaimer,
         fall back to who spoke first: the channel with the earliest speech
         segment is the agent, since the agent answers the phone first.

    Args:
        left_segments: The (start, end, text) segments from the left channel.
        right_segments: The (start, end, text) segments from the right channel.

    Returns:
        A tuple (left_speaker, right_speaker) where each value is SPEAKER_AGENT
        or SPEAKER_BOT.
    """
    left_has_disclaimer = channel_contains_disclaimer(left_segments)
    right_has_disclaimer = channel_contains_disclaimer(right_segments)

    # Primary rule: exactly one channel carries the disclaimer.
    if left_has_disclaimer and not right_has_disclaimer:
        return SPEAKER_AGENT, SPEAKER_BOT
    if right_has_disclaimer and not left_has_disclaimer:
        return SPEAKER_BOT, SPEAKER_AGENT

    # Fallback rule: the channel that spoke first is the agent.
    if earliest_start_seconds(left_segments) <= earliest_start_seconds(right_segments):
        return SPEAKER_AGENT, SPEAKER_BOT
    return SPEAKER_BOT, SPEAKER_AGENT


def merge_channels_into_timeline(
    left_segments: list[tuple[float, float, str]],
    left_speaker: str,
    right_segments: list[tuple[float, float, str]],
    right_speaker: str,
) -> list[TranscriptSegment]:
    """Merge both channels' segments into one timeline ordered by start time.

    Args:
        left_segments: The (start, end, text) segments from the left channel.
        left_speaker: The speaker label for the left channel.
        right_segments: The (start, end, text) segments from the right channel.
        right_speaker: The speaker label for the right channel.

    Returns:
        One list of TranscriptSegment covering both speakers, sorted by start
        time so the conversation reads in the order it happened.
    """
    merged = []
    for start, end, text in left_segments:
        merged.append(TranscriptSegment(left_speaker, start, end, text))
    for start, end, text in right_segments:
        merged.append(TranscriptSegment(right_speaker, start, end, text))

    merged.sort(key=lambda segment: segment.start_seconds)
    return merged


def render_transcript_text(segments: list[TranscriptSegment]) -> str:
    """Turn labeled, ordered segments into the final transcript text.

    Each line looks like "[12.3s] AGENT: ..." or "[12.3s] BOT: ...".

    Args:
        segments: The merged, time-ordered, speaker-labeled segments.

    Returns:
        The whole transcript as one string, one segment per line.
    """
    lines = []
    for segment in segments:
        timestamp = f"[{segment.start_seconds:.1f}s]"
        lines.append(f"{timestamp} {segment.speaker}: {segment.text}")
    return "\n".join(lines)


def transcribe_recording(wav_path: Path) -> Transcript:
    """Turn a dual-channel WAV recording into a clean, speaker-labeled transcript.

    This is the main entry point of the file. It splits the stereo recording into
    its two channels, transcribes each one separately, decides which channel is
    the agent and which is the bot, merges everything into one timeline, writes
    the result to the transcripts directory, and returns it.

    Args:
        wav_path: Path to the dual-channel (stereo) WAV recording. The file name
            stem is used as the transcript file name, for example
            "CA....wav" produces "CA....txt".

    Returns:
        A Transcript holding the labeled full text and the time-ordered segments.

    Raises:
        FileNotFoundError: If wav_path does not point to a real file.
        ValueError: If the WAV is not stereo (two channels).
    """
    wav_path = Path(wav_path)

    settings = load_settings()
    model_size = settings.get("models", {}).get("offline_transcribe_model", "base")
    transcriber = load_whisper_model(model_size)

    left_path, right_path = split_stereo_wav_to_mono_files(wav_path)
    try:
        left_segments, language = transcribe_one_channel(left_path, transcriber)
        right_segments, _right_language = transcribe_one_channel(
            right_path, transcriber
        )
    finally:
        # Clean up the temporary per-channel WAV files no matter what happens.
        left_path.unlink(missing_ok=True)
        right_path.unlink(missing_ok=True)

    left_speaker, right_speaker = assign_speakers(left_segments, right_segments)
    merged_segments = merge_channels_into_timeline(
        left_segments, left_speaker, right_segments, right_speaker
    )
    full_text = render_transcript_text(merged_segments)

    transcript = Transcript(
        audio_path=str(wav_path),
        full_text=full_text,
        segments=merged_segments,
        language=language,
        model_name=model_size,
    )

    output_path = transcript_output_path(wav_path)
    save_transcript(transcript, output_path)
    print(f"Saved labeled transcript to {output_path}")

    return transcript


def transcript_output_path(wav_path: Path) -> Path:
    """Work out where the transcript for a recording should be written.

    Args:
        wav_path: Path to the WAV recording. Its file name stem becomes the
            transcript file name.

    Returns:
        The path to the transcript file, for example
        "results/transcripts/CA....txt", using the transcripts_dir from
        config/settings.yaml.
    """
    settings = load_settings()
    transcripts_dir = settings.get("paths", {}).get(
        "transcripts_dir", "results/transcripts"
    )
    return Path(transcripts_dir) / f"{wav_path.stem}.txt"


def save_transcript(transcript: Transcript, output_path: Path) -> None:
    """Write a transcript's labeled text to disk for humans and the analyzer.

    Args:
        transcript: The transcript to save.
        output_path: Where to write the transcript file, for example a .txt file.

    Returns:
        Nothing. The transcript's full_text is written to output_path. The parent
        directory is created if it does not already exist.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(transcript.full_text + "\n", encoding="utf-8")


def resolve_wav_path(wav_argument: str, sid_argument: str) -> Path:
    """Work out the WAV path from either an explicit path or a call SID.

    Args:
        wav_argument: The --wav value, an explicit path to a WAV file, or None.
        sid_argument: The --sid value, a Twilio call SID used to build the path
            from the recordings directory, or None.

    Returns:
        The resolved path to the WAV recording.

    Raises:
        ValueError: If neither argument is given, so the caller gets a clear
            message instead of a confusing failure later.
    """
    if wav_argument:
        return Path(wav_argument)

    if sid_argument:
        settings = load_settings()
        recordings_dir = settings.get("paths", {}).get(
            "recordings_dir", "results/recordings"
        )
        return Path(recordings_dir) / f"{sid_argument}.wav"

    raise ValueError(
        "Give either --wav (a path to the dual-channel WAV) or --sid (the Twilio "
        "call SID) so the WAV can be found in the recordings directory."
    )


def main() -> None:
    """Parse command line arguments and transcribe one dual-channel recording.

    What goes in:
        Nothing directly. Reads --wav (a path to the WAV) or --sid (a Twilio call
        SID) from the command line. One of the two is required.

    What comes out:
        Nothing is returned. The labeled transcript is written to the transcripts
        directory and printed to the screen.
    """
    parser = argparse.ArgumentParser(
        description="Transcribe a dual-channel Twilio call recording into a "
        "clean transcript with AGENT and BOT labels."
    )
    parser.add_argument(
        "--wav",
        default=None,
        help="Path to the dual-channel WAV recording to transcribe.",
    )
    parser.add_argument(
        "--sid",
        default=None,
        help="Twilio call SID. The WAV is looked up as <recordings_dir>/<sid>.wav.",
    )
    arguments = parser.parse_args()

    wav_path = resolve_wav_path(arguments.wav, arguments.sid)
    transcript = transcribe_recording(wav_path)

    print()
    print(transcript.full_text)


if __name__ == "__main__":
    main()

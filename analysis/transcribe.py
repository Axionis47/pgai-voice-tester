"""Offline transcription of a saved call recording.

After a call ends, the live speech to text result is good enough for the bot to
talk in real time, but it is not clean enough to judge what the agent actually
said. This file re-transcribes the saved audio file from scratch using Whisper
or faster-whisper, which is slower but more accurate. The clean transcript it
produces is the input for the analyzer.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptSegment:
    """One chunk of speech from the recording.

    Attributes:
        speaker: Who is talking. Either "agent" (the medical receptionist AI)
            or "patient" (our bot). May be "unknown" if speakers were not split.
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
    """The full clean transcript of one call.

    Attributes:
        audio_path: The recording this transcript was made from.
        full_text: The whole call as one block of text, in spoken order.
        segments: The call broken into timed chunks. Empty if segmentation
            was not requested.
        language: The detected spoken language, for example "en".
        model_name: The transcription model that produced this, for the record.
    """

    audio_path: str
    full_text: str
    segments: list[TranscriptSegment]
    language: str
    model_name: str


def load_transcriber(model_name: str, device: str) -> object:
    """Load the offline transcription model once so it can be reused.

    Loading a Whisper model is slow, so the caller loads it a single time and
    passes the loaded model into transcribe_recording for each file.

    Args:
        model_name: Which model size to load, for example "base" or "large-v3".
        device: Where to run it, for example "cpu" or "cuda".

    Returns:
        The loaded model object, ready to transcribe audio.
    """
    # Steps the real version will take:
    #   1. Import faster_whisper (preferred) or whisper.
    #   2. Build the model with model_name and device.
    #   3. Return the model object so it can be reused across calls.
    raise NotImplementedError("load_transcriber is not implemented yet.")


def transcribe_recording(
    audio_path: Path,
    transcriber: object,
    split_speakers: bool = False,
) -> Transcript:
    """Turn a saved recording into a clean, accurate transcript.

    This is the main entry point of the file. Give it the path to a saved call
    recording and a loaded model, and it returns the words that were spoken.

    Args:
        audio_path: Path to the saved audio file (for example a .wav of the call).
        transcriber: A model object returned by load_transcriber.
        split_speakers: If true, try to label each chunk as agent or patient and
            fill in the segments list. If false, return one block of text.

    Returns:
        A Transcript holding the full text and, when asked, the timed segments.

    Raises:
        FileNotFoundError: If audio_path does not point to a real file.
    """
    # Steps the real version will take:
    #   1. Check that audio_path exists, raise FileNotFoundError if not.
    #   2. Run the transcriber over the audio to get text and timestamps.
    #   3. If split_speakers is true, assign each chunk to agent or patient.
    #   4. Join the chunks into full_text in spoken order.
    #   5. Build and return a Transcript object.
    raise NotImplementedError("transcribe_recording is not implemented yet.")


def save_transcript(transcript: Transcript, output_path: Path) -> None:
    """Write a transcript to disk so the analyzer and humans can read it.

    Args:
        transcript: The transcript to save.
        output_path: Where to write the transcript file (for example a .json).

    Returns:
        Nothing. The transcript is written to output_path.
    """
    # Steps the real version will take:
    #   1. Convert the Transcript into a plain dictionary.
    #   2. Write it to output_path as JSON (or another agreed format).
    raise NotImplementedError("save_transcript is not implemented yet.")

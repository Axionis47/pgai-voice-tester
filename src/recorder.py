# Saves the audio of a call to disk.
#
# The recorder captures the full conversation between the patient bot and the
# agent and writes it to the recordings folder as an ogg or mp3 file. The saved
# file is what the offline transcription step reads later to build a transcript.
#
# This file does plain mechanics only. It does not decide anything about the call.

from typing import Any


class CallRecorder:
    """Records one phone call and saves the audio to disk.

    The recorder is started at the beginning of a call, receives the call's audio
    while the conversation runs, and is stopped at the end. On stop it writes the
    captured audio to the recordings path as a single ogg or mp3 file and returns
    the path to that file so the rest of the system knows where it landed.
    """

    def __init__(self, recordings_path: str, audio_format: str) -> None:
        """Set up a recorder for one call.

        What goes in:
            recordings_path: folder where the finished audio file should be saved,
                for example results/recordings.
            audio_format: the file format to save in, either "ogg" or "mp3".

        What comes out:
            Nothing. It stores the path and format and prepares an empty buffer to
            collect audio into once recording starts.
        """
        # Steps the real implementation will take:
        # 1. Store recordings_path and audio_format on self.
        # 2. Confirm audio_format is one we support ("ogg" or "mp3").
        # 3. Prepare an empty in-memory buffer to hold audio until stop is called.
        raise NotImplementedError("CallRecorder.__init__ is not implemented yet.")

    def start(self, call_id: str) -> None:
        """Begin recording the call.

        What goes in:
            call_id: a unique id for this call, used to name the output file so
                recordings from different calls do not overwrite each other.

        What comes out:
            Nothing. After this returns, the recorder is ready to accept audio.
        """
        # Steps the real implementation will take:
        # 1. Store the call_id so stop can build the output filename from it.
        # 2. Make sure the recordings folder exists, creating it if needed.
        # 3. Mark the recorder as active so add_audio knows it may collect frames.
        raise NotImplementedError("CallRecorder.start is not implemented yet.")

    def add_audio(self, audio_chunk: Any) -> None:
        """Add one chunk of call audio to the recording.

        What goes in:
            audio_chunk: a piece of raw audio from the call stream, handed in as
                the conversation runs round by round.

        What comes out:
            Nothing. The chunk is appended to the buffer for this call.
        """
        # Steps the real implementation will take:
        # 1. Confirm the recorder is active (start was called, stop was not).
        # 2. Append the audio chunk to the in-memory buffer in arrival order.
        raise NotImplementedError("CallRecorder.add_audio is not implemented yet.")

    def stop(self) -> str:
        """Finish recording and write the audio file to disk.

        What goes in:
            Nothing.

        What comes out:
            The full path to the saved audio file, so callers know where the
            recording lives for transcription later.
        """
        # Steps the real implementation will take:
        # 1. Mark the recorder as no longer active so no more audio is collected.
        # 2. Build the output path from recordings_path, the call_id, and format.
        # 3. Encode the buffered audio into the chosen format and write the file.
        # 4. Return the path to the written file.
        raise NotImplementedError("CallRecorder.stop is not implemented yet.")

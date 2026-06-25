# Downloads the audio recording of a finished call from Twilio.
#
# When place_call.py places a call with dual-channel recording turned on, Twilio
# records each side of the conversation on its own audio channel and keeps the
# audio on its servers. This script fetches that audio and saves it locally so it
# can be transcribed and attached to the bug report.
#
# It saves the recording in two formats:
#   - A WAV file. This keeps the two channels separate (stereo), which is what
#     the transcriber needs to tell the agent and the bot apart.
#   - An MP3 file. This is a mixed mono copy that satisfies the challenge's
#     ogg/mp3 deliverable.
#
# Twilio finishes processing a recording a few seconds after the call ends, so
# this script polls until the recording's status is "completed" before
# downloading. A recording resource can exist before its media is ready; trying
# to download too early returns a 404.
#
# Typical use (after a call placed with place_call.py has ended):
#   python download_recording.py --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# The saved files land at results/recordings/<callSid>.wav and
# results/recordings/<callSid>.mp3 by default.

import argparse
import os
import time

import requests

from src.clients import build_twilio_client, _require_env, load_settings


# How long to keep checking Twilio for a completed recording before giving up,
# in seconds. Twilio usually has the recording ready within a few seconds of the
# call ending, but we allow some slack for processing.
RECORDING_POLL_TIMEOUT_SECONDS = 30

# How long to wait between checks while polling, in seconds.
RECORDING_POLL_INTERVAL_SECONDS = 3

# Twilio reports this status once a recording's media is fully processed and
# ready to download. Downloading before this point can return a 404.
RECORDING_STATUS_COMPLETED = "completed"


def default_recordings_dir() -> str:
    """Return the recordings directory from settings, or a sensible default.

    What goes in:
        Nothing. It reads paths.recordings_dir from config/settings.yaml.

    What comes out:
        The directory path where recordings should be saved, for example
        "results/recordings". Falls back to "results/recordings" if the setting
        is missing so the script still works without a complete config.
    """
    settings = load_settings()
    paths = settings.get("paths", {})
    return paths.get("recordings_dir", "results/recordings")


def wait_for_completed_recording(call_sid: str):
    """Poll Twilio until the call's recording is completed, or the timeout passes.

    A recording resource can appear on Twilio before its audio media has finished
    processing. Downloading the media at that point returns a 404, so we wait for
    the recording's status to become "completed" before handing it back.

    What goes in:
        call_sid: the Twilio call SID returned by place_call.py, for example
            "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".

    What comes out:
        The completed Twilio recording object for that call, or None if no
        completed recording appears before the timeout. A recording can be
        missing because the call was too short to record, or because Twilio is
        still processing it.
    """
    twilio_client = build_twilio_client()

    deadline = time.monotonic() + RECORDING_POLL_TIMEOUT_SECONDS
    while True:
        recordings = twilio_client.recordings.list(call_sid=call_sid)
        if recordings and recordings[0].status == RECORDING_STATUS_COMPLETED:
            return recordings[0]

        if time.monotonic() >= deadline:
            return None

        print("Recording not ready yet, checking again in a few seconds...")
        time.sleep(RECORDING_POLL_INTERVAL_SECONDS)


def build_media_url(recording_uri: str, extension: str) -> str:
    """Turn a Twilio recording uri into a downloadable media URL for one format.

    What goes in:
        recording_uri: the recording's uri from Twilio, a path that ends in
            ".json", for example
            "/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.json".
        extension: the audio format to ask Twilio for, without a leading dot,
            for example "wav" or "mp3".

    What comes out:
        The full https URL of the recording's media in that format, for example
        "https://api.twilio.com/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.wav".
        Twilio serves the same recording at the same path with either a .wav or
        .mp3 extension. The .wav keeps the two channels separate; the .mp3 is a
        mixed mono copy.
    """
    # The uri ends in ".json"; swapping that for the wanted extension gives the
    # audio media URL for that format.
    path_without_extension = recording_uri.rsplit(".json", 1)[0]
    return f"https://api.twilio.com{path_without_extension}.{extension}"


def download_media(media_url: str, save_path: str) -> None:
    """Download the media at the given Twilio URL and write it to disk.

    What goes in:
        media_url: the full https URL of the recording's media (wav or mp3).
        save_path: the local file path to write the audio to.

    What comes out:
        Nothing is returned. The audio bytes are written to save_path. The Twilio
        media endpoint requires the account credentials, so we pass them as HTTP
        basic auth. Raises an error if the download fails.
    """
    account_sid = _require_env("TWILIO_ACCOUNT_SID")
    auth_token = _require_env("TWILIO_AUTH_TOKEN")

    response = requests.get(media_url, auth=(account_sid, auth_token))
    response.raise_for_status()

    with open(save_path, "wb") as audio_file:
        audio_file.write(response.content)


def download_recording(call_sid: str, output_dir: str) -> None:
    """Find, download, and save the WAV and MP3 recordings for one call.

    The WAV keeps the two audio channels separate so the transcriber can tell the
    agent from the bot. The MP3 is a mixed mono copy kept for the challenge's
    ogg/mp3 deliverable. Both are downloaded here.

    What goes in:
        call_sid: the Twilio call SID of the call whose recording we want.
        output_dir: the directory to save the audio into. It is created if needed.

    What comes out:
        Nothing is returned. On success it prints the saved file paths. If no
        completed recording is found before the timeout, it prints a clear
        message explaining the likely reasons instead of failing.
    """
    recording = wait_for_completed_recording(call_sid)
    if recording is None:
        print(
            f"No completed recording found for call {call_sid} after "
            f"{RECORDING_POLL_TIMEOUT_SECONDS} seconds. The call may have been "
            "too short to record, or Twilio may still be processing it. "
            "Wait a moment and try again."
        )
        return

    os.makedirs(output_dir, exist_ok=True)

    wav_path = os.path.join(output_dir, f"{call_sid}.wav")
    mp3_path = os.path.join(output_dir, f"{call_sid}.mp3")

    wav_url = build_media_url(recording.uri, "wav")
    mp3_url = build_media_url(recording.uri, "mp3")

    download_media(wav_url, wav_path)
    download_media(mp3_url, mp3_path)

    print(f"Saved dual-channel recording to {wav_path}")
    print(f"Saved mixed mono recording to {mp3_path}")


def main() -> None:
    """Parse command line arguments and download one call's recording.

    What goes in:
        Nothing directly. Reads --sid (required) and --dir (optional) from the
        command line. --sid is the Twilio call SID printed by place_call.py.
        --dir overrides the recordings directory from settings.yaml.

    What comes out:
        Nothing is returned. Prints the saved file paths, or a message explaining
        why no recording could be downloaded.
    """
    parser = argparse.ArgumentParser(
        description="Download a Twilio call recording as both a dual-channel "
        "WAV file and a mixed mono MP3 file."
    )
    parser.add_argument(
        "--sid",
        required=True,
        help="The Twilio call SID to download the recording for. This is the SID "
        "printed by place_call.py when the call was placed.",
    )
    parser.add_argument(
        "--dir",
        default=None,
        help="Directory to save the audio into. Defaults to the recordings_dir in "
        "config/settings.yaml (results/recordings).",
    )
    arguments = parser.parse_args()

    output_dir = arguments.dir if arguments.dir else default_recordings_dir()
    download_recording(arguments.sid, output_dir)


if __name__ == "__main__":
    main()

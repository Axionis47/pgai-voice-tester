# Downloads the audio recording of a finished call from Twilio as an MP3 file.
#
# When place_call.py places a call with recording turned on, Twilio records both
# sides and keeps the audio on its servers. This script fetches that audio and
# saves it locally so it can be transcribed and attached to the bug report.
#
# Twilio finishes processing a recording a few seconds after the call ends, so
# this script polls for a short while before giving up.
#
# Typical use (after a call placed with place_call.py has ended):
#   python download_recording.py --sid CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# The saved file lands at results/recordings/<callSid>.mp3 by default.

import argparse
import os
import time

import requests

from src.clients import build_twilio_client, _require_env, load_settings


# How long to keep checking Twilio for a recording before giving up, in seconds.
# Twilio usually has the recording ready within a few seconds of the call ending,
# but we allow some slack for processing.
RECORDING_POLL_TIMEOUT_SECONDS = 30

# How long to wait between checks while polling, in seconds.
RECORDING_POLL_INTERVAL_SECONDS = 3


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


def wait_for_recording(call_sid: str):
    """Poll Twilio until the call's recording is ready, or the timeout passes.

    What goes in:
        call_sid: the Twilio call SID returned by place_call.py, for example
            "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".

    What comes out:
        The first Twilio recording object for that call, or None if no recording
        appears before the timeout. A recording can be missing because the call
        was too short to record, or because Twilio is still processing it.
    """
    twilio_client = build_twilio_client()

    deadline = time.monotonic() + RECORDING_POLL_TIMEOUT_SECONDS
    while True:
        recordings = twilio_client.recordings.list(call_sid=call_sid)
        if recordings:
            return recordings[0]

        if time.monotonic() >= deadline:
            return None

        print("Recording not ready yet, checking again in a few seconds...")
        time.sleep(RECORDING_POLL_INTERVAL_SECONDS)


def build_mp3_media_url(recording_uri: str) -> str:
    """Turn a Twilio recording uri into its downloadable MP3 media URL.

    What goes in:
        recording_uri: the recording's uri from Twilio, a path that ends in
            ".json", for example
            "/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.json".

    What comes out:
        The full https URL of the recording's MP3 media, for example
        "https://api.twilio.com/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.mp3".
        Twilio serves the same recording as .mp3 or .wav depending on the
        extension; we ask for .mp3 because the challenge accepts mp3.
    """
    # The uri ends in ".json"; swapping that for ".mp3" gives the audio media URL.
    path_without_extension = recording_uri.rsplit(".json", 1)[0]
    return f"https://api.twilio.com{path_without_extension}.mp3"


def download_mp3(media_url: str, save_path: str) -> None:
    """Download the MP3 at the given Twilio URL and write it to disk.

    What goes in:
        media_url: the full https URL of the recording's MP3 media.
        save_path: the local file path to write the MP3 to.

    What comes out:
        Nothing is returned. The MP3 bytes are written to save_path. The Twilio
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
    """Find, download, and save the MP3 recording for one call.

    What goes in:
        call_sid: the Twilio call SID of the call whose recording we want.
        output_dir: the directory to save the MP3 into. It is created if needed.

    What comes out:
        Nothing is returned. On success it prints the saved file path. If no
        recording is found before the timeout, it prints a clear message
        explaining the likely reasons instead of failing.
    """
    recording = wait_for_recording(call_sid)
    if recording is None:
        print(
            f"No recording found for call {call_sid} after "
            f"{RECORDING_POLL_TIMEOUT_SECONDS} seconds. The call may have been "
            "too short to record, or Twilio may still be processing it. "
            "Wait a moment and try again."
        )
        return

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{call_sid}.mp3")

    media_url = build_mp3_media_url(recording.uri)
    download_mp3(media_url, save_path)

    print(f"Saved recording to {save_path}")


def main() -> None:
    """Parse command line arguments and download one call's recording.

    What goes in:
        Nothing directly. Reads --sid (required) and --dir (optional) from the
        command line. --sid is the Twilio call SID printed by place_call.py.
        --dir overrides the recordings directory from settings.yaml.

    What comes out:
        Nothing is returned. Prints the saved file path, or a message explaining
        why no recording could be downloaded.
    """
    parser = argparse.ArgumentParser(
        description="Download a Twilio call recording as an MP3 file."
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
        help="Directory to save the MP3 into. Defaults to the recordings_dir in "
        "config/settings.yaml (results/recordings).",
    )
    arguments = parser.parse_args()

    output_dir = arguments.dir if arguments.dir else default_recordings_dir()
    download_recording(arguments.sid, output_dir)


if __name__ == "__main__":
    main()

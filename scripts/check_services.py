# Connectivity checker for every external service the voice tester depends on.
# Run this before placing the first call to confirm each account is set up:
#   python scripts/check_services.py
# Each check makes a minimal real connection and reports OK or FAIL with a plain
# message. Fill in .env one service at a time and watch them turn green. The
# script exits non-zero if any check fails, so it can also gate automation.

import asyncio
import os
import sys
from pathlib import Path
from typing import Tuple

# Make the project root importable so "from src.clients import ..." works no
# matter which directory the script is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.clients import (  # noqa: E402  (import after sys.path setup)
    build_gemini_client,
    build_twilio_client,
    load_environment,
    load_settings,
    load_whisper_model,
)


# A check result is just a pass/fail flag plus a short human-readable message.
CheckResult = Tuple[bool, str]


def check_gemini_text() -> CheckResult:
    """Confirm the Gemini text path works by asking for a one-word reply.

    What goes in:
        Nothing. It builds the Gemini client from config and environment.

    What comes out:
        A (passed, message) pair. Passed is True if Gemini returned any text.
        This proves the brain and analyzer path: the same client and Vertex AI
        project used to decide the patient's lines and analyze the finished call.

    Any missing key or unreachable service is turned into a failing result with
    a helpful message instead of a crash.
    """
    try:
        settings = load_settings()
        brain_model = settings.get("models", {}).get("brain_model", "gemini-2.5-flash")

        client = build_gemini_client()
        response = client.models.generate_content(
            model=brain_model,
            contents="Reply with the single word: ok",
        )

        reply_text = (response.text or "").strip()
        if reply_text == "":
            return (False, f"{brain_model} connected but returned no text.")
        return (True, f"{brain_model} replied: {reply_text!r}")
    except Exception as error:
        return (False, _describe_error(error))


def check_gemini_live() -> CheckResult:
    """Confirm the Gemini Live voice path by opening and closing a session.

    What goes in:
        Nothing. It builds the Gemini client and reads the live model id and
        voice from settings.

    What comes out:
        A (passed, message) pair. Passed is True if a Live session opened over
        Vertex AI. This proves the real-time voice loop the call will use. We do
        not send any audio; opening the streaming session is enough to verify it.

    The Live API is asynchronous, so this runs a small async helper and waits for
    it. Any failure becomes a failing result with a helpful message.
    """
    try:
        return asyncio.run(_open_and_close_live_session())
    except Exception as error:
        return (False, _describe_error(error))


async def _open_and_close_live_session() -> CheckResult:
    """Open a Gemini Live session, confirm it connected, then close it.

    What goes in:
        Nothing. It builds the client and reads the live model id and voice name
        from settings.

    What comes out:
        A (passed, message) pair. Passed is True once the streaming session is
        open. The session is closed automatically when the context block exits.

    This is the smallest real test of the live path: connect and disconnect.
    """
    settings = load_settings()
    models = settings.get("models", {})
    voice = settings.get("voice", {})

    live_model = models.get("live_model", "gemini-2.0-flash-live-preview-04-09")
    voice_name = voice.get("voice_name", "Aoede")

    client = build_gemini_client()

    # Ask for an audio voice response so the config matches how the real call
    # runs. A minimal config is enough to prove the session opens.
    live_config = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {"voice_name": voice_name}
            }
        },
    }

    async with client.aio.live.connect(model=live_model, config=live_config):
        # Reaching this point means the websocket handshake succeeded.
        return (True, f"{live_model} live session opened and closed cleanly.")


def check_twilio() -> CheckResult:
    """Confirm Twilio credentials work by fetching the account.

    What goes in:
        Nothing. It builds the Twilio client from environment credentials.

    What comes out:
        A (passed, message) pair. Passed is True if Twilio returns the account
        for the given SID and token. No call is placed here; this only checks
        that the credentials are valid.

    A wrong or missing SID or token becomes a failing result with a helpful
    message rather than a raw Twilio exception.
    """
    try:
        load_environment()
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")

        client = build_twilio_client()
        account = client.api.accounts(account_sid).fetch()

        return (True, f"Twilio account active (status: {account.status}).")
    except Exception as error:
        return (False, _describe_error(error))


def check_whisper() -> CheckResult:
    """Confirm the offline Whisper model loads and is ready.

    What goes in:
        Nothing. It reads the model size from settings
        (models.offline_transcribe_model) and loads it locally.

    What comes out:
        A (passed, message) pair. Passed is True once the model is loaded. This
        runs fully on the local machine with no network or credentials, so it
        only fails if faster-whisper is missing or the weights cannot be fetched
        on the very first load.

    The first load of a size downloads weights once and may take a few seconds.
    """
    try:
        settings = load_settings()
        model_size = settings.get("models", {}).get("offline_transcribe_model", "base")

        load_whisper_model(model_size)
        return (True, f"Whisper model {model_size!r} loaded and ready.")
    except Exception as error:
        return (False, _describe_error(error))


def _describe_error(error: Exception) -> str:
    """Turn an exception into a short, plain-English failure message.

    What goes in:
        error: any exception raised while a check was running.

    What comes out:
        A one-line string naming the error type and its message, safe to print
        in the results table. This keeps the output readable instead of dumping
        a full traceback.
    """
    error_type = type(error).__name__
    error_message = str(error).strip()
    if error_message == "":
        return error_type
    return f"{error_type}: {error_message}"


def _print_results_table(results) -> None:
    """Print the check results as a simple aligned table.

    What goes in:
        results: a list of (service_name, passed, message) tuples.

    What comes out:
        Nothing is returned. It prints one row per service: the name, OK or FAIL,
        and the message, lined up so the table is easy to scan.
    """
    name_width = max(len(name) for name, _, _ in results)

    print("")
    print("Service check results")
    print("-" * 60)
    for service_name, passed, message in results:
        status = "OK  " if passed else "FAIL"
        print(f"{service_name.ljust(name_width)}  {status}  {message}")
    print("-" * 60)


def main() -> int:
    """Run every service check, print the results table, and report failures.

    What goes in:
        Nothing.

    What comes out:
        A process exit code: 0 if every check passed, 1 if any check failed.
        The caller (and the shell) can use this to gate further steps.
    """
    # Pair each service name with the function that checks it, in the order a
    # user is likely to set the accounts up.
    checks = [
        ("Gemini text", check_gemini_text),
        ("Gemini Live", check_gemini_live),
        ("Twilio", check_twilio),
        ("Whisper", check_whisper),
    ]

    results = []
    for service_name, check_function in checks:
        passed, message = check_function()
        results.append((service_name, passed, message))

    _print_results_table(results)

    any_failed = any(not passed for _, passed, _ in results)
    if any_failed:
        print("Some checks failed. Fix the items marked FAIL and run again.")
        return 1

    print("All services reachable. You are ready to place a call.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

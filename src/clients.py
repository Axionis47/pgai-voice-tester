# Builds the external service clients the voice tester depends on.
# This is the one place that reads credentials and turns config plus environment
# into ready-to-use clients: the Gemini client (text and Live voice on Vertex AI),
# the Twilio REST client, and the local Whisper transcription model. Nothing here
# places a call or generates anything; it only constructs clients.

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.config_loader import load_settings as _load_settings_from_config


# Where the project root is, found relative to this file so the path works no
# matter which directory the program is started from. load_environment uses it
# to find the .env file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_environment() -> None:
    """Load variables from the project .env file into the process environment.

    What goes in:
        Nothing. It looks for a ".env" file at the project root.

    What comes out:
        Nothing is returned. After this runs, values from .env are available
        through os.environ. If there is no .env file, nothing happens and any
        variables already set in the real environment are used as-is.

    Keeping this in one function means every client loads credentials the same
    way and we never read the .env file in more than one place.
    """
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)


def load_settings() -> Dict[str, Any]:
    """Read config/settings.yaml and return it as a plain dictionary.

    What goes in:
        Nothing. The settings file path is fixed at the project root.

    What comes out:
        A dictionary of every setting in the file (models, voice, telephony,
        and so on). Raises FileNotFoundError if the settings file is missing.

    Config files are read in one place (config_loader), so this delegates there
    instead of opening the file itself. The no-argument signature is kept because
    several scripts call load_settings() this way.
    """
    return _load_settings_from_config()


def _require_env(variable_name: str) -> str:
    """Read one required environment variable or fail with a clear message.

    What goes in:
        variable_name: the name of the environment variable to read, for
            example "GOOGLE_CLOUD_PROJECT".

    What comes out:
        The variable's value as a string. Raises RuntimeError with a plain
        message naming the missing variable if it is not set or is blank.

    This gives every client the same friendly error when a credential is
    missing, instead of a confusing failure deep inside a third-party library.
    """
    value = os.environ.get(variable_name)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Environment variable {variable_name} is not set. "
            f"Add it to your .env file (see .env.example)."
        )
    return value


def build_gemini_client():
    """Build the google-genai client pointed at Vertex AI.

    What goes in:
        Nothing directly. It reads the project and region from the environment
        variables named in settings.yaml (GOOGLE_CLOUD_PROJECT and
        GOOGLE_CLOUD_LOCATION), and reads use_vertexai from settings.

    What comes out:
        A configured google-genai Client. The same client is used for both text
        generation (the brain and analyzer) and the Live voice session, so we
        build it once here. Raises RuntimeError if a required variable is missing.

    Authentication uses Application Default Credentials. The path to the service
    account JSON is read by the Google libraries from GOOGLE_APPLICATION_CREDENTIALS,
    so we do not pass credentials by hand here.
    """
    load_environment()
    settings = load_settings()
    vertex_settings = settings.get("vertex", {})

    project_env_name = vertex_settings.get("project_env", "GOOGLE_CLOUD_PROJECT")
    location_env_name = vertex_settings.get("location_env", "GOOGLE_CLOUD_LOCATION")
    use_vertexai = vertex_settings.get("use_vertexai", True)

    project_id = _require_env(project_env_name)
    location = _require_env(location_env_name)

    # Import here so simply importing this module does not require the SDK to be
    # installed; the import only runs when someone actually builds the client.
    from google import genai

    return genai.Client(
        vertexai=use_vertexai,
        project=project_id,
        location=location,
    )


def build_twilio_client():
    """Build the Twilio REST client from environment credentials.

    What goes in:
        Nothing directly. It reads TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN from
        the environment.

    What comes out:
        A configured Twilio REST Client used to place the outbound call. Raises
        RuntimeError if either credential is missing.

    This only builds the client. It does not dial anyone.
    """
    load_environment()

    account_sid = _require_env("TWILIO_ACCOUNT_SID")
    auth_token = _require_env("TWILIO_AUTH_TOKEN")

    # Import here so this module imports cleanly even before twilio is installed;
    # the import only runs when someone actually builds the client.
    from twilio.rest import Client as TwilioClient

    return TwilioClient(account_sid, auth_token)


def load_whisper_model(model_size: str):
    """Load a faster-whisper model for offline, local transcription.

    What goes in:
        model_size: the Whisper model size to load, for example "base" or
            "small". This usually comes from settings.yaml
            (models.offline_transcribe_model).

    What comes out:
        A loaded faster-whisper model ready to transcribe audio. This runs fully
        on the local machine, so no network or credentials are needed. The first
        load of a given size downloads the model weights once and caches them.

    Loading can take a few seconds the first time while weights are fetched.
    """
    # Import here so this module imports cleanly even before faster-whisper is
    # installed; the import only runs when someone actually loads a model.
    from faster_whisper import WhisperModel

    return WhisperModel(model_size)

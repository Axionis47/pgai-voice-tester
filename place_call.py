# Places the outbound phone call that kicks off a live test.
#
# Twilio dials the destination number and, the moment the call connects, opens a
# websocket back to our bridge server's /stream endpoint (see server.py). The TwiML
# below is what tells Twilio to do that. The <Connect><Stream> verb makes the audio
# bidirectional, so the bridge can both hear the call and speak back into it.
#
# Typical use (after the server and a cloudflared tunnel are running):
#   python place_call.py --to +1YOURNUMBER --url your-tunnel-host.trycloudflare.com
#
# The --url is just the public host from cloudflared, with no scheme. This script
# turns it into the wss://<host>/stream URL that Twilio connects back to.

import argparse
import os

from src.clients import build_twilio_client, load_settings, load_environment, _require_env


def build_stream_twiml(media_stream_url: str, scenario_name: str) -> str:
    """Build the TwiML that tells Twilio to open a two-way media stream.

    What goes in:
        media_stream_url: the full wss:// URL of our bridge's /stream endpoint,
            for example "wss://my-tunnel.trycloudflare.com/stream".
        scenario_name: the scenario id to pass through to the server as a custom
            parameter, so the bridge knows which patient to play.

    What comes out:
        A TwiML XML string. <Connect><Stream> is bidirectional, so the bridge can
        send audio back to the caller. The <Parameter> rides along and shows up on
        the server under start.customParameters.
    """
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Response>"
        "<Connect>"
        f"<Stream url=\"{media_stream_url}\">"
        f"<Parameter name=\"scenario\" value=\"{scenario_name}\"/>"
        "</Stream>"
        "</Connect>"
        "</Response>"
    )


def build_stream_url_from_host(public_host: str) -> str:
    """Turn a bare cloudflared host into the wss:// stream URL Twilio dials back.

    What goes in:
        public_host: the public host from cloudflared, with no scheme, for example
            "my-tunnel.trycloudflare.com". A leading "https://" or "wss://" is
            tolerated and stripped so the caller does not have to be careful.

    What comes out:
        The full secure websocket URL of the bridge's /stream endpoint, for
        example "wss://my-tunnel.trycloudflare.com/stream".
    """
    # Strip any scheme the user may have pasted, so we always end up with wss://.
    host_only = public_host
    for prefix in ("https://", "http://", "wss://", "ws://"):
        if host_only.startswith(prefix):
            host_only = host_only[len(prefix):]
    host_only = host_only.rstrip("/")
    return f"wss://{host_only}/stream"


def place_call(destination_number: str, public_host: str, scenario_name: str) -> str:
    """Place the outbound call and return the Twilio call SID.

    What goes in:
        destination_number: the number to dial, in E.164 form (for example
            "+18055551234"). For the first test this is your own phone.
        public_host: the public cloudflared host (no scheme) that fronts the
            bridge server.
        scenario_name: the scenario id to run, passed to the bridge as a stream
            parameter.

    What comes out:
        The Twilio call SID as a string. The call itself is now ringing.
    """
    load_environment()
    settings = load_settings()

    # The caller id we dial out from is named in settings and stored in the env.
    from_number_env = settings.get("telephony", {}).get(
        "from_number_env", "TWILIO_FROM_NUMBER"
    )
    from_number = _require_env(from_number_env)

    media_stream_url = build_stream_url_from_host(public_host)
    twiml = build_stream_twiml(media_stream_url, scenario_name)

    twilio_client = build_twilio_client()
    call = twilio_client.calls.create(
        to=destination_number,
        from_=from_number,
        twiml=twiml,
    )
    return call.sid


def main() -> None:
    """Parse command line arguments and place one outbound call.

    What goes in:
        Nothing directly. Reads --to, --url, and --scenario from the command line.
        --to defaults to the TARGET_NUMBER environment variable when omitted.

    What comes out:
        Nothing is returned. Prints the Twilio call SID so you can track the call.
    """
    parser = argparse.ArgumentParser(
        description="Place an outbound Twilio call wired to the Gemini Live bridge."
    )
    parser.add_argument(
        "--to",
        default=os.environ.get("TARGET_NUMBER"),
        help="Destination number in E.164 form (defaults to TARGET_NUMBER env var). "
        "For the first test, pass your own phone number.",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Public cloudflared host with no scheme, for example "
        "my-tunnel.trycloudflare.com. The wss://HOST/stream URL is built from it.",
    )
    parser.add_argument(
        "--scenario",
        default="example_scenario",
        help="Scenario id to run (a file name under config/scenarios/ without the "
        ".yaml). Defaults to example_scenario.",
    )
    arguments = parser.parse_args()

    if not arguments.to:
        parser.error(
            "No destination number. Pass --to +1YOURNUMBER or set TARGET_NUMBER."
        )

    call_sid = place_call(arguments.to, arguments.url, arguments.scenario)
    print(f"Call placed. SID: {call_sid}")


if __name__ == "__main__":
    main()

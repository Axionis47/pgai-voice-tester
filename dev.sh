#!/usr/bin/env bash
#
# dev.sh
# Runs one complete test call end to end with a single command.
#
# What it does:
#   1. Finds a working Python 3.11+ interpreter.
#   2. Creates a Python virtual environment in .venv (if missing) and uses it.
#   3. Installs the pinned dependencies from requirements.txt.
#   4. Starts the bridge server (server.py) in the background on port 8080.
#   5. Opens a cloudflared tunnel to that port and reads back the public host.
#   6. Places one call to the target agent using the chosen scenario.
#   7. Waits for the call to finish, then downloads and transcribes the recording.
#   8. Prints the transcript and recording paths, then shuts the server and
#      tunnel down on exit.
#
# Prerequisites:
#   - cloudflared (the Cloudflare tunnel client)
#   - a filled-in .env file (copy .env.example to .env first)
#   - Python 3.11 or newer
#
# Usage:
#   ./dev.sh                              # uses the sample_hours_location scenario
#   ./dev.sh <scenario-name>             # uses the named scenario
#
# A scenario name is a file under config/scenarios/ without the .yaml suffix,
# for example sample_hours_location or probe_price_multiservice.

set -euo pipefail

# Always work from the directory this script lives in.
cd "$(dirname "$0")"

# Pick the scenario from the first argument, defaulting to a simple sample call.
SCENARIO="${1:-sample_hours_location}"

# Find the first interpreter that actually runs and is Python 3.11 or newer.
# A bare python3 can be a broken shim on some machines, so we test each candidate
# by running it, not by trusting that it exists.
find_python() {
  local candidates=(
    python3
    python3.12
    python3.11
    python
    /usr/local/bin/python3.12
    /opt/homebrew/bin/python3
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  echo "No working Python 3.11+ found"
  exit 1
fi
echo "Using Python: $PYTHON"

# Create the virtual environment once, then activate it. After this point the
# plain python and pip commands are the ones inside .venv.
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment in .venv ..."
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Install dependencies quietly.
echo "Installing dependencies ..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# The .env file holds the secrets and settings. Stop early if it is missing.
if [ ! -f ".env" ]; then
  echo "No .env file found."
  echo "Copy .env.example to .env and fill it in, then run ./dev.sh again."
  exit 1
fi

# Start the bridge server in the background and remember its process id.
echo "Starting bridge server (logs in server.log) ..."
python server.py > server.log 2>&1 &
SERVER_PID=$!

# Start the cloudflared tunnel in the background and remember its process id.
echo "Starting cloudflared tunnel (logs in tunnel.log) ..."
cloudflared tunnel --url http://localhost:8080 > tunnel.log 2>&1 &
TUNNEL_PID=$!

# Kill both background processes when this script exits, no matter why it exits.
cleanup() {
  echo ""
  echo "Shutting down ..."
  kill "$SERVER_PID" "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for cloudflared to print its public host. Try for about 20 seconds.
echo "Waiting for the tunnel host ..."
TUNNEL_HOST=""
for _ in $(seq 1 20); do
  TUNNEL_HOST="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1 || true)"
  if [ -n "$TUNNEL_HOST" ]; then
    break
  fi
  sleep 1
done

if [ -z "$TUNNEL_HOST" ]; then
  echo "Could not find the tunnel host. Check tunnel.log for details."
  exit 1
fi

# place_call.py wants a bare host with no scheme, so strip the https:// part.
BARE_HOST="${TUNNEL_HOST#https://}"

# Record how many calls have already finished so we can tell when ours ends.
# grep -c prints the count (0 when nothing matches) but exits 1 on zero matches,
# so guard it against set -e with || true.
BASE=$(grep -c "connection closed" server.log 2>/dev/null || true)

# Place the call and capture the Twilio SID from place_call.py's output. It prints
# a line like "Call placed. SID: CA...". Omitting --to dials the target agent by
# design, which is what we want here.
echo "Placing the call (scenario: $SCENARIO) ..."
SID="$(python place_call.py --url "$BARE_HOST" --scenario "$SCENARIO" | grep -oE 'CA[0-9a-f]{32}' | head -1 || true)"
if [ -z "$SID" ]; then
  echo "Could not read the call SID from place_call.py. Check the output above."
  exit 1
fi
echo "Call SID: $SID"

# Wait for the call to finish. The server logs "connection closed" when the call
# websocket ends, so we watch for that count to go above the baseline.
echo "Waiting for the call to finish ..."
for _ in $(seq 1 150); do
  CUR=$(grep -c "connection closed" server.log 2>/dev/null || true)
  if [ "$CUR" -gt "$BASE" ]; then
    break
  fi
  sleep 2
done

# Download the recording, then transcribe it offline.
echo "Downloading the recording ..."
python download_recording.py --sid "$SID"
echo "Transcribing the recording ..."
python analysis/transcribe.py --sid "$SID"

# Print a clear final block. After this the script ends and the trap shuts the
# server and tunnel down.
echo ""
echo "===================================================================="
echo " Test call complete."
echo ""
echo " Transcript: results/transcripts/$SID.txt"
echo " Recording:  results/recordings/$SID.mp3"
echo "===================================================================="

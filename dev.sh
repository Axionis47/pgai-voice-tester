#!/usr/bin/env bash
#
# dev.sh
# Brings the voice tester up with one command.
#
# What it does:
#   1. Creates a Python virtual environment in .venv (if missing) and uses it.
#   2. Installs the pinned dependencies from requirements.txt.
#   3. Starts the bridge server (server.py) in the background on port 8080.
#   4. Opens a cloudflared tunnel to that port and reads back the public host.
#   5. Prints the tunnel host and the exact command to place a call.
#
# Prerequisites:
#   - python3
#   - cloudflared (the Cloudflare tunnel client)
#   - a filled-in .env file (copy .env.example to .env first)
#
# Usage:
#   ./dev.sh
#
# Press Ctrl+C to stop. The script cleans up the server and tunnel on exit.

set -euo pipefail

# Always work from the directory this script lives in.
cd "$(dirname "$0")"

# Create the virtual environment once, then activate it.
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment in .venv ..."
  python3 -m venv .venv
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

# Kill both background processes when this script exits (including Ctrl+C).
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
  TUNNEL_HOST="$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" tunnel.log | head -1 || true)"
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

# Print a clear, ready-to-use block.
echo ""
echo "===================================================================="
echo " Voice tester is ready."
echo ""
echo " Tunnel host: $BARE_HOST"
echo ""
echo " In another terminal, place a call:"
echo "   python place_call.py --url $BARE_HOST --scenario sample_hours_location"
echo ""
echo " (Omit --to to dial the target agent.)"
echo ""
echo " Press Ctrl+C here to stop the server and tunnel."
echo "===================================================================="

# Stay up until interrupted so the server and tunnel keep running.
wait

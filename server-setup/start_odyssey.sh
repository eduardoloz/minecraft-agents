#!/bin/bash
# Usage: ./start_odyssey.sh [api_port]
#   api_port  Port for the REST API server (default: 8000)
#
# Bots are spawned at runtime via the API — see server.js for endpoints.
# Each bot needs a unique mineflayer port, passed when spawning via POST /bots.
API_PORT="${1:-8000}"

# Activate the venv so child bot_runner.py processes inherit the right python
source ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/venv/bin/activate

cd ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/Odyssey/Odyssey
node server.js "$API_PORT"

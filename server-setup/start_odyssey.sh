#!/bin/bash
NODE_PORT="${1:-3000}"
MC_USERNAME="${2:-bot}"

export ODYSSEY_NODE_PORT="$NODE_PORT"
export ODYSSEY_USERNAME="$MC_USERNAME"

source ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/venv/bin/activate
cd ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/Odyssey/Odyssey
python main.py

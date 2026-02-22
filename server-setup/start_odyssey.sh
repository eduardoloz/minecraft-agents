API_PORT="${1:-8000}"

source ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/venv/bin/activate

cd ~/MINECRAFTEXPERIMENTS/AgenticMinecraft/Odyssey/Odyssey
node server.js "$API_PORT"

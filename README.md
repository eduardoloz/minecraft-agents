# minecraft-agents

A **hopper hacks 2026** project integrating LLM agents with Minecraft, using the Odyssey framework as its upstream agent core.

## Directory Structure

```
minecraft-agents/
├── Odyssey/              # Upstream Odyssey framework (LLM agent core)
├── docker/               # (planned) Docker setup for parallel agents
├── custom_skills/        # (planned) Custom skill extensions
├── ui/                   # (planned) Monitoring dashboard
├── server-setup/         # Server infrastructure (venv, data, mods, scripts)
└── README.md
```

## Planned Components

**docker/** - Enables spinning up multiple isolated Minecraft servers with corresponding agent containers in parallel, each with independent resources.

**custom_skills/** - Houses extensions to Odyssey's skill library, keeping new primitive and compositional skills separate from upstream code.

**ui/** - Provides monitoring capabilities for agent state, task progression, and logging across multiple concurrent agents.

## Setup Requirements

### Prerequisites
- Python >= 3.9
- Node.js >= 16.13.0
- Running Minecraft server instance
- Running LLaMA-3 backend

### Installation Steps

1. **Clone repository** and navigate into directory

2. **Create Python virtual environment**:
   ```bash
   python -m venv server-setup/venv
   source server-setup/venv/bin/activate
   ```

3. **Install Python packages**:
   ```bash
   cd Odyssey/Odyssey
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Install Node dependencies**:
   ```bash
   npm install -g yarn
   cd Odyssey/Odyssey/odyssey/env/mineflayer
   yarn install
   cd mineflayer-collectblock
   npx tsc
   cd ../node_modules/mineflayer-collectblock
   npx tsc
   ```

5. **Configure settings**: Copy config template and populate:
   ```bash
   cp Odyssey/Odyssey/conf/config.json.keep.this Odyssey/Odyssey/conf/config.json
   ```
   Populate with LLM API credentials, server addresses, and embedding model path.
   > **config.json is gitignored — never commit it. It contains secrets.**

6. **Download embedding model** (requires [git-lfs](https://git-lfs.com)):
   ```bash
   git lfs install
   git clone https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.git server-setup/embeddings
   ```

## Running

**Terminal 1 — Start the Minecraft server** (via docker-compose in `server-setup/`):
```bash
cd server-setup
docker compose up
```

**Terminal 2 — Start LLM backend** (once server is running):
```bash
~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/start_llm_backend.sh
```

**Terminal 3 — Start Odyssey agent** (once backend is running):
```bash
~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/start_odyssey.sh
```

## Key Configuration Values (`Odyssey/Odyssey/conf/config.json`)
- `api_key`: LLM authentication
- `server_host` / `server_port`: LLM backend address
- `MC_SERVER_HOST` / `MC_SERVER_PORT`: Minecraft server connection
- `SENTENT_EMBEDDING_DIR`: Local path to embedding model
- `NODE_SERVER_PORT`: Node.js service port

## License
MIT License

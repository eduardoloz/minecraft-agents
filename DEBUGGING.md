# DEBUGGING.md

A comprehensive guide for diagnosing issues across the three services that make up this stack: the Minecraft server (Docker), the LLM Backend (FastAPI), and the Odyssey agent (Python + mineflayer Node.js).

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Port Map](#port-map)
3. [Quick Health Check](#quick-health-check)
4. [Service 1: Minecraft Server (Docker)](#service-1-minecraft-server-docker)
5. [Service 2: LLM Backend (FastAPI)](#service-2-llm-backend-fastapi)
6. [Service 3: Odyssey Agent (Python + mineflayer)](#service-3-odyssey-agent-python--mineflayer)
   - [The Python Agent Layer](#the-python-agent-layer)
   - [The Mineflayer Node.js Layer](#the-mineflayer-nodejs-layer)
7. [How the Chat Interface Works](#how-the-chat-interface-works)
8. [Log File Reference](#log-file-reference)
9. [Common Error Patterns](#common-error-patterns)
10. [Layered Isolation: Which Service Is to Blame?](#layered-isolation-which-service-is-to-blame)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Host Machine                                                   │
│                                                                 │
│  ┌──────────────────────┐    ┌────────────────────────────────┐ │
│  │  Odyssey Python Agent│    │  LLM Backend (FastAPI/uvicorn) │ │
│  │  Odyssey/Odyssey/    │    │  Odyssey/LLM-Backend/          │ │
│  │  main.py             │───▶│  localhost:<server_port>       │ │
│  │                      │    │  /llama3_8b_v3, /ping, etc.    │ │
│  │  VoyagerEnv          │    └────────────────────────────────┘ │
│  │     │                │                                       │
│  │     │ HTTP POST       │                                       │
│  │     ▼                │                                       │
│  │  localhost:3000       │                                       │
│  │  (NODE_SERVER_PORT)   │                                       │
│  └──────────────────────┘                                       │
│           │                                                     │
│           │ subprocess (node index.js 3000)                     │
│           ▼                                                     │
│  ┌──────────────────────┐    ┌────────────────────────────────┐ │
│  │  Mineflayer          │    │  Minecraft Server (Docker)     │ │
│  │  Node.js/Express     │◀──▶│  itzg/minecraft-server         │ │
│  │  localhost:3000      │    │  Paper 1.19.4                  │ │
│  │                      │    │  host:25573 → container:25565  │ │
│  └──────────────────────┘    └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Startup order matters:**

1. `docker compose up` — Minecraft server must be fully ready first
2. `start_llm_backend.sh` — LLM backend must be ready before Odyssey calls models
3. `start_odyssey.sh` — Agent last; it will attempt mineflayer connection immediately

---

## Port Map

| Service | Host Port | Container/Internal | Protocol | Notes |
|---|---|---|---|---|
| Minecraft server | `25573` | `25565` | TCP (MC protocol) | Docker maps host→container |
| Mineflayer Express API | `3000` | — | HTTP | `NODE_SERVER_PORT` in config.json |
| LLM Backend (FastAPI) | configured | — | HTTP | `server_port` in LLM-Backend config |
| LLM Backend `/ping` | same | — | HTTP | Health-check endpoint |

**Critical:** The MC connection in `config.json` (`MC_SERVER_PORT`) must be the **host-side port** `25573`, not the container-internal port `25565`. The agent runs on the host and reaches the container through the Docker port mapping.

---

## Quick Health Check

Run these in order to confirm each service is alive before chasing bugs:

```bash
# 1. Is the Minecraft container running?
docker ps | grep mc

# 2. Can the host reach the MC server port?
nc -zv 127.0.0.1 25573

# 3. Is the LLM backend up? (replace PORT with server_port from config.json)
curl http://127.0.0.1:<PORT>/ping
# Expected: {"data":"pong!"}

# 4. Is mineflayer running? (only exists while Odyssey is running)
curl -s http://127.0.0.1:3000/
# Any response (even 404) means the Express server is up.
# "Connection refused" means mineflayer is not running.

# 5. Is the bot currently connected to the MC server?
# Check the MC server log:
tail -f server-setup/data/logs/latest.log | grep -E "joined|left|logged in"
```

---

## Service 1: Minecraft Server (Docker)

### Starting and watching

```bash
cd server-setup
docker compose up          # foreground — shows all server output
docker compose up -d       # detached
docker compose logs -f     # follow logs from detached container
docker compose logs -f mc  # same but explicit service name
```

### Entering the container console

The container is started with `tty: true` and `stdin_open: true`, which enables the interactive RCON console:

```bash
# Attach to the running container's stdin (gives you a live server console)
docker attach $(docker compose ps -q mc)
# Detach without stopping: Ctrl+P, Ctrl+Q

# Run a one-off command via docker exec
docker exec -it $(docker compose ps -q mc) rcon-cli
# Then type commands: op bot, list, gamemode creative bot, etc.
```

### Key log file: `server-setup/data/logs/latest.log`

This is the **ground truth** for what the server sees. Check here to confirm:

- Bot joined/left: `bot joined the game` / `bot left the game` / `bot lost connection: Disconnected`
- Bot chat messages: `<bot> SUCCESS: 3 cobblestone...` / `<bot> FAILED: only 2...`
- Bot slash commands: `bot issued server command: /kill @s`
- Player joins: `SpookyPenguino joined the game`
- Player chat: `<SpookyPenguino> Can you get 1 piece of wood?`
- Errors/crashes: stack traces from Paper/plugins

```bash
# Live tail with timestamps
tail -f server-setup/data/logs/latest.log

# Filter to only bot/player activity
tail -f server-setup/data/logs/latest.log | grep -v "^\[Server thread\]" | grep -E "bot|<"

# Show the last 100 lines (useful after a crash)
tail -100 server-setup/data/logs/latest.log

# Grep for connection events
grep -E "joined|left the game|lost connection|logged in" server-setup/data/logs/latest.log
```

### Checking server config

Key settings live in `server-setup/data/server.properties`:

```
online-mode=false        # Must be false — bot connects without a Mojang account
server-port=25565        # Container-internal port (host sees 25573)
enable-rcon=true         # Allows docker rcon-cli access
```

OPs are set in `docker-compose.yaml` under `OPS:`. Bot user (`bot`) must be an op or commands like `/give`, `/tp`, `/kill`, `/gamerule` will silently fail.

### Server not starting / staying crashed

```bash
# Check exit code
docker compose ps

# Full stdout from the container
docker compose logs mc | tail -100

# Common cause: EULA not accepted — handled automatically by EULA: "TRUE" in compose
# Common cause: Port 25573 already in use on host
sudo ss -tlnp | grep 25573
```

---

## Service 2: LLM Backend (FastAPI)

### Starting

```bash
~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/start_llm_backend.sh
# Equivalent to:
source server-setup/venv/bin/activate
cd Odyssey/LLM-Backend
python main.py
```

The backend starts uvicorn on `0.0.0.0:<port>` where port comes from `Odyssey/LLM-Backend/conf/config.json`.

### Config file

`Odyssey/LLM-Backend/conf/config.json` (gitignored):

```json
{
    "api_key": "...",        // Gemini API key
    "port": 8000             // port uvicorn listens on
}
```

### Health checks

```bash
# Ping
curl http://127.0.0.1:<PORT>/ping
# {"data":"pong!"}

# Current concurrent request count
curl http://127.0.0.1:<PORT>/status
# {"concurrent_requests": 0}

# Test a model route directly (llama3_8b_v3, llama3_8b, llama3_70b_v1, etc.)
curl -X POST http://127.0.0.1:<PORT>/llama3_8b_v3 \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "say hello", "system_prompt": "you are helpful"}'
```

### Diagnosing LLM call failures

If the Odyssey agent logs show errors when calling the LLM:

1. Confirm the backend is running (`/ping`)
2. Check `server_host` and `server_port` in `Odyssey/Odyssey/conf/config.json` match where the backend is actually listening
3. Send a direct POST (above) to isolate whether it's a network issue or an API-key/model issue
4. Check uvicorn stderr output for Python exceptions — typically shown inline when running `start_llm_backend.sh` in foreground

### LLM-Backend config vs Odyssey config

There are **two separate config.json files**:

| File | Used by | Key fields |
|---|---|---|
| `Odyssey/LLM-Backend/conf/config.json` | LLM Backend (FastAPI) | `api_key`, `port` |
| `Odyssey/Odyssey/conf/config.json` | Odyssey Python agent | `MC_SERVER_HOST`, `MC_SERVER_PORT`, `NODE_SERVER_PORT`, `server_host`, `server_port`, `SENTENT_EMBEDDING_DIR` |

`server_host` + `server_port` in the **Odyssey config** must point to where the LLM backend is running.

---

## Service 3: Odyssey Agent (Python + mineflayer)

### Starting

```bash
~/MINECRAFTEXPERIMENTS/AgenticMinecraft/server-setup/start_odyssey.sh
# Equivalent to:
source server-setup/venv/bin/activate
cd Odyssey/Odyssey
python main.py
```

### The Python Agent Layer

**Config file:** `Odyssey/Odyssey/conf/config.json`

```json
{
    "api_key": "...",
    "server_host": "http://127.0.0.1",   // LLM backend host
    "server_port": "8000",                // LLM backend port
    "NODE_SERVER_PORT": 3000,             // mineflayer Express port
    "SENTENT_EMBEDDING_DIR": "/path/to/model",
    "MC_SERVER_HOST": "127.0.0.1",       // Minecraft server host
    "MC_SERVER_PORT": "25573"            // Host-side Docker port!
}
```

**Key Python components:**

- `Odyssey/Odyssey/odyssey/env/bridge.py` — `VoyagerEnv` — Gymnasium environment that wraps all HTTP calls to mineflayer. Methods: `reset()`, `step(code)`, `pause()`, `unpause()`, `close()`
- `Odyssey/Odyssey/odyssey/env/process_monitor.py` — `SubprocessMonitor` — spawns and monitors Node.js as a subprocess, captures stdout to a timestamped log file

**Python logs:**

Odyssey uses a Python `logging` module logger (`get_logger('main')`, `get_logger('VoyagerEnv')`). By default, output goes to stdout. Look for:

```
INFO:VoyagerEnv:reset node server
INFO:VoyagerEnv:Start Mineflayer process
INFO:VoyagerEnv:mineflayer ready line: Server started on port 3000
CRITICAL:main:<exception message>   # caught exceptions in the inference loop
```

**Startup sequence inside `VoyagerEnv.reset()`:**

1. Calls `mineflayer.stop()` to kill any existing Node process
2. Sleeps 1 second
3. Calls `check_process()`:
   - Spawns `node index.js 3000` as a subprocess
   - Waits until stdout matches `"Server started on port (\d+)"`
   - POSTs to `http://127.0.0.1:3000/start` with `{host, port, reset, inventory, equipment, spread, waitTicks, username}`
4. On success, `has_reset = True`, `connected = True`

### The Mineflayer Node.js Layer

**Source:** `Odyssey/Odyssey/odyssey/env/mineflayer/index.js`

**What it is:** An Express HTTP server that accepts commands from Python and controls a mineflayer Minecraft bot. It runs as a long-lived subprocess managed by `SubprocessMonitor`.

**Endpoints:**

| Route | Method | What it does |
|---|---|---|
| `/start` | POST | Creates a new mineflayer bot, connects to MC server, waits for spawn |
| `/step` | POST | `eval()`s the provided JS code with the bot in scope, returns `bot.observe()` |
| `/stop` | POST | Disconnects the bot (`bot.end()`) |
| `/pause` | POST | Sends `/pause` chat command to MC server; toggles pause state |

**`/start` request body:**

```json
{
    "host": "127.0.0.1",
    "port": "25573",
    "username": "bot",
    "reset": "hard",        // "hard" = /clear + /kill on spawn; "soft" = skip
    "inventory": {},        // items to /give after hard reset
    "equipment": [],        // armor/weapon slots for hard reset
    "spread": false,        // whether to /spreadplayers the bot
    "waitTicks": 100,       // how many ticks to wait between operations
    "position": null        // optional {x, y, z} to /tp bot on spawn
}
```

**`/step` request body:**

```json
{
    "code": "await mineBlock(bot, 'log', 3);",
    "programs": "// helper function definitions injected here"
}
```

The code is evaluated inside an async IIFE: `(async () => { <programs>\n<code> })()`. Any thrown error is caught by `handleError()`, which maps it back to the line in `code` that caused it.

**Mineflayer log files:**

Each time `SubprocessMonitor.run()` is called, a new timestamped log is created:

```
Odyssey/Odyssey/logs/mineflayer/YYYYMMDD_HHMMSS.log
```

These are the most important files for debugging bot behavior. They capture all Node.js stdout/stderr, including:

- Connection events (what host/port the bot tried to connect to)
- All error stack traces from `eval()`'d code
- `No path to <block> at (x, y, z)! Skip it!` — pathfinding failures
- `Digging aborted! Skip it!` — mining interruptions
- `physicTick` deprecation warnings (harmless noise)
- `TypeError: res.json is not a function` — response already sent (race condition)

```bash
# Find the most recent mineflayer log
ls -t Odyssey/Odyssey/logs/mineflayer/*.log | head -1

# Tail it
tail -f $(ls -t Odyssey/Odyssey/logs/mineflayer/*.log | head -1)

# Grep for errors only
grep -i "error\|failed\|exception\|uncaught" \
  $(ls -t Odyssey/Odyssey/logs/mineflayer/*.log | head -1)
```

---

## How the Chat Interface Works

Understanding chat is essential for knowing what the bot is "saying" and what players can say to it.

### Bot → Minecraft (outbound chat)

The bot sends chat via `bot.chat("message")` in the mineflayer JS code. This appears in:

- **In-game** for all players as `<bot> message`
- **Server log** (`server-setup/data/logs/latest.log`) as:
  ```
  [Async Chat Thread - #N/INFO]: [Not Secure] <bot> message
  ```
- **Mineflayer log** — only if the bot's own messages trigger a `chatEvent` (they generally don't for its own messages)

The bot also uses `bot.chat("/command")` for slash commands (e.g., `/give @s diamond`). These appear in server logs as:
```
[Server thread/INFO]: bot issued server command: /give @s diamond
[Server thread/INFO]: [bot: Gave 1 [Diamond] to bot]
```

### Player → Bot (inbound chat)

When a player types in chat, mineflayer fires a `chatEvent`. This is captured by `onChat.js`:

```js
// lib/observation/onChat.js
bot.on("chatEvent", (username, message) => {
    if (message.startsWith("/")) return;  // ignore slash commands
    this.obs += message;
    this.bot.event(this.name);
});
```

The accumulated chat (`this.obs`) is included in the next `bot.observe()` call that Python receives after `/step`. **Chat is not processed in real-time** — it's batched into the observation returned at the end of each step.

**This means:** Players can type in game chat, but the bot only "reads" it at the end of the current step execution. There is no live conversational loop unless the Odyssey skill code explicitly checks `chatObs`.

### Observation structure

`bot.observe()` (defined in `lib/observation/base.js`) is a JSON object aggregating all observation modules. After each `/step`, Python receives:

```json
{
    "status": { ... },       // health, food, position, biome, time-of-day
    "inventory": { ... },    // itemsByName
    "voxels": { ... },       // nearby block types
    "onChat": "message",     // accumulated player chat since last step
    "onError": "...",        // any bot errors
    "onSave": ...,
    "chests": { ... },
    "blockRecords": { ... }
}
```

### Verifying the bot is talking to the right server

1. In the mineflayer log, the `/start` payload is logged at the top of each session:
   ```
   INFO - { host: '127.0.0.1', port: '25573', username: 'bot', ... }
   ```
2. In the MC server log you should see:
   ```
   bot joined the game
   ```
3. If those two are aligned but the bot still can't run commands, check that `bot` is in the `ops.json` on the server:
   ```bash
   cat server-setup/data/ops.json
   ```

---

## Log File Reference

| Log | Location | What to look for |
|---|---|---|
| **MC server (latest)** | `server-setup/data/logs/latest.log` | Bot joins/leaves, chat messages, slash commands, server errors |
| **MC server (archive)** | `server-setup/data/logs/YYYY-MM-DD-N.log.gz` | Historical sessions (`zcat` to read) |
| **Mineflayer (current)** | `Odyssey/Odyssey/logs/mineflayer/<latest>.log` | Bot JS errors, pathfinding failures, connection params |
| **Mineflayer (all)** | `Odyssey/Odyssey/logs/mineflayer/` | One file per `SubprocessMonitor.run()` call |
| **Odyssey Python** | stdout of `start_odyssey.sh` | Agent-level INFO/CRITICAL, step timing, LLM errors |
| **LLM Backend** | stdout of `start_llm_backend.sh` | uvicorn access log, API key errors, model exceptions |
| **Docker container** | `docker compose logs mc` | Server startup, EULA, JVM errors, plugin load |

---

## Common Error Patterns

### "Connection refused" on port 25573

**Symptom:** Bot fails to connect; mineflayer log shows `ECONNREFUSED`.

**Causes:**
- Docker container not running → `docker compose up`
- Wrong port in `MC_SERVER_PORT` (must be `25573`, not `25565`)
- Server still starting up (Paper takes ~30s on first run)

---

### "Connection refused" on port 3000

**Symptom:** Python logs `requests.exceptions.ConnectionError` when calling `http://127.0.0.1:3000/start`.

**Cause:** Mineflayer subprocess hasn't started yet, or crashed before setting up Express.

**Check:**
```bash
# Is node running at all?
ps aux | grep node

# Check the latest mineflayer log for a crash
tail -20 $(ls -t Odyssey/Odyssey/logs/mineflayer/*.log | head -1)
```

---

### "Bot not spawned" (400 from /pause)

**Symptom:** Mineflayer returns `400 {"error": "Bot not spawned"}` when Python calls `/pause`.

**Cause:** Python called `/pause` before `/start` completed (or the bot was disconnected between steps).

**Root cause:** The bot may have been kicked, died and the `keepInventory` gamerule isn't set yet, or the MC server restarted.

---

### `TypeError: res.json is not a function`

**Symptom:** In the mineflayer log:
```
TypeError: res.json is not a function
    at /...index.js:249:13
```

**Cause:** The response was already sent (e.g., by the error handler) and then the normal response path tried to send again.

**Impact:** The current step result is lost; Python may receive an HTTP error or timeout. The next reset/step will restart mineflayer and recover.

---

### `physicTick` deprecation warnings

**Symptom:** Mineflayer log spammed with:
```
Mineflayer detected that you are using a deprecated event (physicTick)!
Please use this event (physicsTick) instead.
```

**Impact:** None — this is a harmless warning from a newer version of mineflayer about old event names. Does not affect functionality.

---

### LLM call failures / timeout

**Symptom:** Python logs `CRITICAL` with a requests timeout or HTTP error from the LLM backend.

**Check:**
1. `curl http://127.0.0.1:<PORT>/ping` — is the backend up?
2. Check `server_host`/`server_port` in `Odyssey/Odyssey/conf/config.json`
3. Check LLM Backend stdout for Python exceptions (bad API key, rate limit, etc.)
4. Check `/status` endpoint for stuck concurrent requests

---

### Bot keeps dying (zombie attacks)

**Symptom:** Server log shows repeated `bot was slain by Zombie`.

**Cause:** Bot is in survival mode with no combat skill active. The `explore` mode doesn't handle mobs.

**Workaround:** Set difficulty to peaceful in the running server via rcon:
```bash
docker exec -it $(docker compose ps -q mc) rcon-cli
# Then:
difficulty peaceful
```

Or add `DIFFICULTY: peaceful` to the docker-compose environment.

---

### `No path to <block>` spam

**Symptom:** Mineflayer log full of `No path to iron_ore at (x, y, z)! Skip it!`

**Cause:** Pathfinder can't navigate to a discovered ore block (underground, across a gap, etc.). The bot will try nearby alternatives. This is expected behavior, not an error.

---

### Embedding model not found

**Symptom:** Odyssey crashes on startup with a file-not-found error referencing `SENTENT_EMBEDDING_DIR`.

**Cause:** The sentence transformer model hasn't been downloaded yet, or the path in config.json is wrong.

**Fix:** Verify the path in `Odyssey/Odyssey/conf/config.json` matches the actual location of the `paraphrase-multilingual-MiniLM-L12-v2` model directory. See README for download instructions.

---

## Layered Isolation: Which Service Is to Blame?

Use this decision tree when something goes wrong:

```
Bot not doing anything / Python crashing
│
├─ Is the MC server reachable?
│   nc -zv 127.0.0.1 25573
│   ├─ NO  → docker compose up; check docker compose logs mc
│   └─ YES → continue
│
├─ Does the MC server log show the bot joining?
│   grep "bot joined" server-setup/data/logs/latest.log
│   ├─ NO  → mineflayer connection problem
│   │         Check latest mineflayer log for ECONNREFUSED / wrong port
│   └─ YES → continue
│
├─ Is the LLM backend responding?
│   curl http://127.0.0.1:<PORT>/ping
│   ├─ NO  → start_llm_backend.sh; check API key / port in both configs
│   └─ YES → continue
│
├─ Is mineflayer's Express server up?
│   curl -s http://127.0.0.1:3000/ (any response = up)
│   ├─ NO  → Odyssey not running, or mineflayer crashed
│   │         Check latest mineflayer log; try python main.py manually
│   └─ YES → continue
│
├─ Does the bot join the server but do nothing?
│   tail -f server-setup/data/logs/latest.log
│   ├─ Bot joins then immediately leaves
│   │   → /start succeeded but /step failed; check mineflayer log for JS errors
│   └─ Bot joins and sends chat
│       → Check Odyssey Python stdout for CRITICAL errors from LLM
│
└─ Bot runs but produces wrong actions?
    → Check mineflayer log for JS eval errors and stack traces
      The error handler maps them back to source lines — look for:
      "at line N: <code snippet> in your code"
```

### Side-by-side session monitoring

Run these in separate terminal panes for full visibility:

```bash
# Terminal 1: MC server
docker compose -f server-setup/docker-compose.yaml logs -f mc

# Terminal 2: Latest mineflayer log (auto-picks newest file)
watch -n 2 "tail -30 \$(ls -t Odyssey/Odyssey/logs/mineflayer/*.log | head -1)"

# Terminal 3: Odyssey agent (run here directly instead of via script)
source server-setup/venv/bin/activate && cd Odyssey/Odyssey && python main.py

# Terminal 4: LLM backend
source server-setup/venv/bin/activate && cd Odyssey/LLM-Backend && python main.py
```

# Odyssey Bot REST API

## Services

| Service | Default Port | Entry Point |
|---------|-------------|-------------|
| Bot Server | `8000` | `node server.js [port]` |
| LLM Backend | configured in `LLM-Backend/conf/config.json` | `python main.py` |

---

## Bot Server (`server.js`)

### Bot Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bots` | Spawn a new bot |
| `GET` | `/bots` | List all bots + their status |
| `GET` | `/bots/:name` | Get a single bot's status |
| `DELETE` | `/bots/:name` | Kill and destroy a bot |

**Spawn body:**
```json
{
  "name": "bot1",
  "port": 3000,
  "username": "Steve",
  "environment": "explore",
  "model": "llama3_8b_v3"
}
```
- `environment`: `explore` | `combat` | `farming` | `subgoal`
- `username`, `environment`, `model` are optional

---

### Bot Actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bots/:name/task` | Free-form task (LLM decomposes it) |
| `POST` | `/bots/:name/subgoal` | Run a pre-defined ordered list of subgoals |
| `POST` | `/bots/:name/explore` | Open-ended exploration / learning loop |
| `POST` | `/bots/:name/skill` | Execute a raw `.js` skill file directly |
| `POST` | `/bots/:name/stop` | Interrupt the currently running task |

All action endpoints support these optional flags:

| Flag | Type | Description |
|------|------|-------------|
| `preempt` | bool | Interrupt current task and run this one next |
| `queue` | bool | Append to task queue instead of running now |
| `reset_env` | bool | Reset the Mineflayer environment first |

**Examples:**

```bash
# Free-form task
curl -X POST http://localhost:8000/bots/bot1/task \
  -H "Content-Type: application/json" \
  -d '{"task": "mine 10 diamonds"}'

# Ordered subgoals
curl -X POST http://localhost:8000/bots/bot1/subgoal \
  -H "Content-Type: application/json" \
  -d '{"task": "get wood", "sub_goals": ["chop oak tree", "collect 10 logs"]}'

# Open-ended exploration
curl -X POST http://localhost:8000/bots/bot1/explore \
  -H "Content-Type: application/json" \
  -d '{"goal": "find a village"}'

# Run a raw skill file
curl -X POST http://localhost:8000/bots/bot1/skill \
  -H "Content-Type: application/json" \
  -d '{"skill_path": "./skill_library/craftWoodenPlanks.js", "parameters": []}'

# Stop current task (and clear queue)
curl -X POST http://localhost:8000/bots/bot1/stop \
  -H "Content-Type: application/json" \
  -d '{"clear_queue": true}'

# Preempt current task with a new one
curl -X POST http://localhost:8000/bots/bot1/task \
  -H "Content-Type: application/json" \
  -d '{"task": "come back to base", "preempt": true}'
```

---

### Task Queue

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/bots/:name/queue` | View pending queued tasks |
| `DELETE` | `/bots/:name/queue` | Clear entire queue |
| `DELETE` | `/bots/:name/queue/:index` | Remove one task by position (0-indexed) |

```bash
# View queue
curl http://localhost:8000/bots/bot1/queue

# Clear queue
curl -X DELETE http://localhost:8000/bots/bot1/queue

# Remove task at position 2
curl -X DELETE http://localhost:8000/bots/bot1/queue/2
```

---

### Bot Status Object

Returned by `GET /bots`, `GET /bots/:name`, and most action endpoints:

```json
{
  "name": "bot1",
  "username": "Steve",
  "port": 3000,
  "status": "idle",
  "currentTask": null,
  "lastResult": null,
  "error": null,
  "queue": []
}
```

- `status`: `starting` | `idle` | `running` | `error` | `dead`

---

## LLM Backend (`LLM-Backend/main.py`)

All model name aliases route to Gemini under the hood.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ping` | Health check |
| `GET` | `/status` | Concurrent request count |
| `POST` | `/<model_name>` | Send a prompt to the LLM |

**Model name aliases:**
- `llama3_8b_v3`
- `llama3_8b`
- `llama3_70b_v1`
- `llama2_70b`
- `qwen2-7b`
- `qwen2-72b`
- `baichuan2-7b`

**LLM request body:**
```json
{
  "user_prompt": "Write a Minecraft skill to craft a pickaxe.",
  "system_prompt": "You are a helpful Minecraft assistant."
}
```

**LLM response:**
```json
{
  "status": 0,
  "data": "<model response text>"
}
```

```bash
# Health check
curl http://localhost:8001/ping

# Call the LLM
curl -X POST http://localhost:8001/llama3_8b_v3 \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "How do I craft a sword?", "system_prompt": "You are a Minecraft expert."}'
```

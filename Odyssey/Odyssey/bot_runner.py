"""
bot_runner.py — One Odyssey bot instance per process.
======================================================
Launched by server.js, one process per bot.

Reads JSON command lines from stdin.
Writes JSON event lines to stdout.
Logs / tracebacks go to stderr (shown in the server terminal).

Commands (stdin, one JSON object per line):
    {"action": "task",    "task": "mine diamonds",          "reset_env": true}
    {"action": "subgoal", "task": "label", "sub_goals": [...], "reset_env": true}
    {"action": "explore", "goal": null,                     "reset_env": true}
    {"action": "skill",   "skill_path": "...", "parameters": [...]}
    {"action": "stop"}
    {"action": "exit"}

Events (stdout, one JSON object per line):
    {"event": "ready"}
    {"event": "started", "label": "..."}
    {"event": "done",    "label": "...", "result": ...}
    {"event": "error",   "label": "...", "message": "..."}
"""

import argparse
import json
import os
import sys
import threading
import traceback
from typing import Optional

# Make the odyssey package importable when running from this directory
sys.path.insert(0, os.path.dirname(__file__))

from odyssey import Odyssey
from odyssey.agents.llama import ModelType
from odyssey.utils import config

# ── Args ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument('--name',        required=True,  help='Bot identifier')
parser.add_argument('--port',        type=int, required=True, help='Mineflayer Node.js port (unique per bot)')
parser.add_argument('--username',    required=True,  help='In-game Minecraft username')
parser.add_argument('--environment', default='explore',
                    choices=['explore', 'combat', 'farming', 'subgoal'],
                    help='Task environment')
parser.add_argument('--model',       default=ModelType.LLAMA3_8B_V3,
                    help='LLM model name for all agents')
args = parser.parse_args()

# ── Odyssey instance ──────────────────────────────────────────────────────────

odyssey = Odyssey(
    mc_port=config.get('MC_SERVER_PORT'),
    mc_host=config.get('MC_SERVER_HOST'),
    env_wait_ticks=100,
    skill_library_dir='./skill_library',
    reload=True,
    embedding_dir=config.get('SENTENT_EMBEDDING_DIR'),
    environment=args.environment,
    resume=False,
    server_port=args.port,
    username=args.username,
    ckpt_dir=f'ckpt/{args.name}',           # per-bot checkpoint dir, avoids conflicts
    action_agent_model_name=args.model,
    critic_agent_model_name=args.model,
    comment_agent_model_name=args.model,
    planner_agent_qa_model_name=args.model,
    planner_agent_model_name=args.model,
)

# ── Output helpers ────────────────────────────────────────────────────────────

_output_lock = threading.Lock()

def emit(msg: dict):
    """Write one JSON event line to stdout (thread-safe)."""
    with _output_lock:
        sys.stdout.write(json.dumps(msg) + '\n')
        sys.stdout.flush()

# ── Task runner ───────────────────────────────────────────────────────────────

_current_thread: Optional[threading.Thread] = None

def _run(label: str, fn, *args, **kwargs):
    """Execute a blocking Odyssey method and emit done/error events."""
    global _current_thread
    emit({'event': 'started', 'label': label})
    try:
        result = fn(*args, **kwargs)
        # Attempt to make the result JSON-serialisable
        try:
            serialisable = json.loads(json.dumps(result, default=str))
        except Exception:
            serialisable = str(result) if result is not None else None
        emit({'event': 'done', 'label': label, 'result': serialisable})
    except Exception as e:
        emit({'event': 'error', 'label': label, 'message': str(e)})
        traceback.print_exc(file=sys.stderr)
    finally:
        _current_thread = None

def dispatch(label: str, fn, *args, **kwargs):
    """Start a task in a background thread. Rejects if already running."""
    global _current_thread
    if _current_thread and _current_thread.is_alive():
        emit({'event': 'error', 'label': label, 'message': 'bot is busy'})
        return
    _current_thread = threading.Thread(
        target=_run, args=(label, fn) + args, kwargs=kwargs, daemon=True
    )
    _current_thread.start()

# ── Command handlers ──────────────────────────────────────────────────────────

def handle(cmd: dict):
    action = cmd.get('action')

    if action == 'task':
        # Free-form task: single rollout (action agent handles retry internally)
        task      = cmd.get('task', '')
        reset_env = cmd.get('reset_env', True)
        dispatch(task, odyssey.rollout, task=task, context='', reset_env=reset_env)

    elif action == 'subgoal':
        # Pre-defined ordered subgoal list, no LLM decomposition
        task      = cmd.get('task', 'subgoal')
        sub_goals = cmd.get('sub_goals', [])
        reset_env = cmd.get('reset_env', True)
        dispatch(f'subgoal: {task}', odyssey.inference_sub_goal,
                 task=task, sub_goals=sub_goals, reset_env=reset_env)

    elif action == 'explore':
        # Open-ended learning loop; goal is optional
        goal      = cmd.get('goal')
        reset_env = cmd.get('reset_env', True)
        label     = f'explore: {goal or "open-ended"}'
        dispatch(label, odyssey.learn, goals=goal, reset_env=reset_env)

    elif action == 'skill':
        # Run a raw .js skill file directly
        skill_path = cmd.get('skill_path', '')
        parameters = cmd.get('parameters', [])
        label      = f'skill: {os.path.basename(skill_path)}'
        dispatch(label, odyssey.run_raw_skill,
                 skill_path=skill_path, parameters=parameters)

    elif action == 'stop':
        # Interrupt the running step via mineflayer's /abort endpoint.
        # This stops the current skill execution and unblocks the task thread
        # without disconnecting the bot from Minecraft.
        if _current_thread and _current_thread.is_alive():
            try:
                import requests as _req
                _req.post(f"{odyssey.env.server}/abort", timeout=5)
            except Exception:
                pass
        else:
            emit({'event': 'error', 'label': '', 'message': 'nothing is running'})

    elif action == 'exit':
        try:
            odyssey.env.close()
        except Exception:
            pass
        sys.exit(0)

    else:
        emit({'event': 'error', 'label': '', 'message': f'unknown action: {action!r}'})

# ── Main loop ─────────────────────────────────────────────────────────────────

emit({'event': 'ready'})

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        cmd = json.loads(line)
    except json.JSONDecodeError as e:
        emit({'event': 'error', 'label': '', 'message': f'invalid JSON: {e}'})
        continue
    handle(cmd)

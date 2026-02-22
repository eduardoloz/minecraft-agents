/**
 * Odyssey Bot REST API Server
 * ============================
 * Run:   node server.js [port]        (default port: 8000)
 * Setup: npm install
 *
 * Each bot runs as a separate bot_runner.py child process.
 * Commands go to Python over stdin (JSON lines).
 * Events come back from Python over stdout (JSON lines).
 *
 * Endpoints
 * ---------
 * POST   /bots                  Spawn a new bot
 * GET    /bots                  List all bots
 * GET    /bots/:name            Get bot status
 * DELETE /bots/:name            Destroy a bot
 * POST   /bots/:name/task       Free-form task (planner decomposes it)
 * POST   /bots/:name/subgoal    Pre-defined ordered subgoal list
 * POST   /bots/:name/explore    Open-ended exploration / learning mode
 * POST   /bots/:name/skill      Run a raw .js skill file
 * POST   /bots/:name/stop       Interrupt the current task
 */

'use strict';

const express   = require('express');
const { spawn } = require('child_process');
const readline  = require('readline');
const path      = require('path');

const app = express();
app.use(express.json());

// name -> BotState
const bots = {};

// ── Bot lifecycle ─────────────────────────────────────────────────────────────

function spawnBot(name, port, username, environment, model) {
    const args = [
        path.join(__dirname, 'bot_runner.py'),
        '--name',        name,
        '--port',        String(port),
        '--username',    username || name,
        '--environment', environment || 'explore',
    ];
    if (model) args.push('--model', model);

    const proc = spawn('python', args, {
        cwd:   __dirname,
        stdio: ['pipe', 'pipe', 'inherit'],  // stdin+stdout piped, stderr straight to terminal
    });

    const state = {
        proc,
        name,
        username:    username || name,
        port,
        status:      'starting',   // starting | idle | running | error | dead
        currentTask: null,
        lastResult:  null,
        error:       null,
    };

    // Read structured events from the Python process
    const rl = readline.createInterface({ input: proc.stdout, crlfDelay: Infinity });
    rl.on('line', (line) => {
        let msg;
        try {
            msg = JSON.parse(line);
        } catch {
            // Raw log / traceback from Python — just print it
            process.stdout.write(`[${name}] ${line}\n`);
            return;
        }

        switch (msg.event) {
            case 'ready':
                state.status = 'idle';
                console.log(`[${name}] ready`);
                break;
            case 'started':
                state.status      = 'running';
                state.currentTask = msg.label;
                state.error       = null;
                console.log(`[${name}] started: ${msg.label}`);
                break;
            case 'done':
                state.status      = 'idle';
                state.currentTask = null;
                state.lastResult  = msg.result ?? null;
                console.log(`[${name}] done: ${msg.label}`);
                break;
            case 'error':
                state.status      = 'error';
                state.currentTask = null;
                state.error       = msg.message;
                console.error(`[${name}] error: ${msg.message}`);
                break;
            default:
                console.log(`[${name}] ${JSON.stringify(msg)}`);
        }
    });

    proc.on('exit', (code) => {
        state.status = 'dead';
        console.log(`[${name}] process exited (code ${code})`);
    });

    return state;
}

function sendCmd(name, cmd) {
    const bot = bots[name];
    if (!bot || bot.status === 'dead') return false;
    bot.proc.stdin.write(JSON.stringify(cmd) + '\n');
    return true;
}

function botInfo(s) {
    return {
        name:        s.name,
        username:    s.username,
        port:        s.port,
        status:      s.status,
        currentTask: s.currentTask,
        lastResult:  s.lastResult,
        error:       s.error,
    };
}

function notFound(name, res) {
    return res.status(404).json({ error: `Bot '${name}' not found` });
}

function busy(state, res) {
    return res.status(409).json({ error: `Bot '${state.name}' is busy: ${state.currentTask}` });
}

// ── Routes ────────────────────────────────────────────────────────────────────

// POST /bots
// Body: { name, port, username?, environment?, model? }
app.post('/bots', (req, res) => {
    const { name, port, username, environment, model } = req.body ?? {};
    if (!name || !port)  return res.status(400).json({ error: "'name' and 'port' are required" });
    if (bots[name])      return res.status(409).json({ error: `Bot '${name}' already exists` });

    const state = spawnBot(name, port, username, environment, model);
    bots[name] = state;
    res.status(201).json(botInfo(state));
});

// GET /bots
app.get('/bots', (req, res) => {
    const result = {};
    for (const [name, state] of Object.entries(bots)) result[name] = botInfo(state);
    res.json(result);
});

// GET /bots/:name
app.get('/bots/:name', (req, res) => {
    const state = bots[req.params.name];
    if (!state) return notFound(req.params.name, res);
    res.json(botInfo(state));
});

// DELETE /bots/:name
app.delete('/bots/:name', (req, res) => {
    const state = bots[req.params.name];
    if (!state) return notFound(req.params.name, res);
    sendCmd(req.params.name, { action: 'exit' });
    setTimeout(() => state.proc.kill(), 500);  // give Python a moment to close cleanly
    delete bots[req.params.name];
    res.json({ status: 'stopped', name: req.params.name });
});

// POST /bots/:name/task
// Body: { task, reset_env? }
app.post('/bots/:name/task', (req, res) => {
    const state = bots[req.params.name];
    if (!state)                   return notFound(req.params.name, res);
    if (state.status === 'running') return busy(state, res);

    const { task, reset_env = true } = req.body ?? {};
    if (!task) return res.status(400).json({ error: "'task' is required" });

    sendCmd(req.params.name, { action: 'task', task, reset_env });
    res.json({ status: 'sent', task });
});

// POST /bots/:name/subgoal
// Body: { sub_goals: string[], task?, reset_env? }
app.post('/bots/:name/subgoal', (req, res) => {
    const state = bots[req.params.name];
    if (!state)                     return notFound(req.params.name, res);
    if (state.status === 'running') return busy(state, res);

    const { task = 'subgoal', sub_goals, reset_env = true } = req.body ?? {};
    if (!Array.isArray(sub_goals) || sub_goals.length === 0)
        return res.status(400).json({ error: "'sub_goals' must be a non-empty array" });

    sendCmd(req.params.name, { action: 'subgoal', task, sub_goals, reset_env });
    res.json({ status: 'sent', task, sub_goals });
});

// POST /bots/:name/explore
// Body: { goal?, reset_env? }
app.post('/bots/:name/explore', (req, res) => {
    const state = bots[req.params.name];
    if (!state)                     return notFound(req.params.name, res);
    if (state.status === 'running') return busy(state, res);

    const { goal = null, reset_env = true } = req.body ?? {};
    sendCmd(req.params.name, { action: 'explore', goal, reset_env });
    res.json({ status: 'sent', goal });
});

// POST /bots/:name/skill
// Body: { skill_path, parameters? }
app.post('/bots/:name/skill', (req, res) => {
    const state = bots[req.params.name];
    if (!state)                     return notFound(req.params.name, res);
    if (state.status === 'running') return busy(state, res);

    const { skill_path, parameters = [] } = req.body ?? {};
    if (!skill_path) return res.status(400).json({ error: "'skill_path' is required" });

    sendCmd(req.params.name, { action: 'skill', skill_path, parameters });
    res.json({ status: 'sent', skill_path, parameters });
});

// POST /bots/:name/stop
app.post('/bots/:name/stop', (req, res) => {
    const state = bots[req.params.name];
    if (!state)                      return notFound(req.params.name, res);
    if (state.status !== 'running')  return res.json({ status: 'already idle', name: req.params.name });

    sendCmd(req.params.name, { action: 'stop' });
    res.json({ status: 'stop signal sent', name: req.params.name });
});

// ── Start ─────────────────────────────────────────────────────────────────────

const PORT = parseInt(process.argv[2] ?? process.env.PORT ?? '8000');
app.listen(PORT, () => {
    console.log(`Odyssey Bot Server on http://0.0.0.0:${PORT}`);
    console.log('  POST   /bots                  spawn a bot');
    console.log('  GET    /bots                  list all bots');
    console.log('  GET    /bots/:name            bot status');
    console.log('  DELETE /bots/:name            destroy a bot');
    console.log('  POST   /bots/:name/task       free-form task');
    console.log('  POST   /bots/:name/subgoal    ordered subgoals');
    console.log('  POST   /bots/:name/explore    exploration mode');
    console.log('  POST   /bots/:name/skill      run JS skill file');
    console.log('  POST   /bots/:name/stop       interrupt task');
});

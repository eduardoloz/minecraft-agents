#!/usr/bin/env node
// Tiny static server to serve the UI and checkpoints/logs without external deps
// Usage: node server-setup/static_server.js [port]

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = parseInt(process.argv[2], 10) || 8000;

const ROOT = path.resolve(__dirname, '..');
const UI_DIR = path.join(ROOT, 'ui');
const CKPT_DIR = path.join(ROOT, 'ckpt');
const LOGS_DIR = path.join(__dirname, 'data', 'logs'); // server-setup/data/logs

function safeJoin(base, p) {
    const resolved = path.resolve(base, '.' + p);
    if (!resolved.startsWith(base)) return null;
    return resolved;
}

function contentType(file) {
    const ext = path.extname(file).toLowerCase();
    switch (ext) {
        case '.html': return 'text/html; charset=utf-8';
        case '.js': return 'application/javascript; charset=utf-8';
        case '.css': return 'text/css; charset=utf-8';
        case '.json': return 'application/json; charset=utf-8';
        case '.png': return 'image/png';
        case '.jpg': case '.jpeg': return 'image/jpeg';
        case '.svg': return 'image/svg+xml';
        case '.gif': return 'image/gif';
        default: return 'application/octet-stream';
    }
}

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    if (req.method === 'OPTIONS') return res.end();

    const parsed = url.parse(req.url);
    let p = decodeURIComponent(parsed.pathname || '/');

    // Route mapping:
    // /            -> ui/index.html
    // /assets/...  -> ui/assets/...
    // /ckpt/...    -> ckpt/...
    // /logs/...    -> server-setup/data/logs/...

    let filePath = null;
    if (p === '/' || p === '/index.html') {
        filePath = path.join(UI_DIR, 'index.html');
    } else if (p.startsWith('/ckpt/')) {
        filePath = safeJoin(CKPT_DIR, p.replace('/ckpt', ''));
    } else if (p.startsWith('/logs/')) {
        filePath = safeJoin(LOGS_DIR, p.replace('/logs', ''));
    } else {
        // default: try under UI
        filePath = safeJoin(UI_DIR, p);
        if (!filePath) {
            // security
            res.statusCode = 404;
            return res.end('Not found');
        }
        // if requesting a directory, serve index.html
        try {
            const stat = fs.statSync(filePath);
            if (stat.isDirectory()) filePath = path.join(filePath, 'index.html');
        } catch (e) { }
    }

    if (!filePath) {
        res.statusCode = 404;
        return res.end('Not found');
    }

    fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
            res.statusCode = 404;
            return res.end('Not found');
        }
        res.setHeader('Content-Type', contentType(filePath));
        const stream = fs.createReadStream(filePath);
        stream.on('error', () => { res.statusCode = 500; res.end('Server error'); });
        stream.pipe(res);
    });
});

server.listen(PORT, () => {
    console.log(`Static server running on http://localhost:${PORT}/`);
    console.log(`UI served from ${UI_DIR}`);
    console.log(`CKPT served from ${CKPT_DIR} at /ckpt/`);
    console.log(`Logs served from ${LOGS_DIR} at /logs/`);
});

// server.js
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 8080;
const clients = new Map();

app.use(express.static(path.join(__dirname, 'public')));

wss.on('connection', (ws) => {
  ws.isAlive = true;
  ws.on('pong', () => (ws.isAlive = true));

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === 'register_client') {
      const clientId = uuidv4();
      ws.clientId = clientId;
      ws.clientName = msg.name || 'Cliente';
      clients.set(clientId, ws);
      ws.send(JSON.stringify({ type: 'registered', clientId }));
      updateTechs();
      return;
    }

    if (msg.type === 'register_tech') {
      ws.isTech = true;
      ws.send(JSON.stringify({ type: 'ack', msg: 'Técnico autenticado' }));
      updateSingleTech(ws);
      return;
    }

    if (msg.type === 'command') {
      const target = clients.get(msg.target);
      if (target && target.readyState === WebSocket.OPEN) {
        target.send(JSON.stringify({ type: 'command', cmd: msg.cmd }));
      }
      return;
    }

    if (msg.type === 'screenshot') {
      broadcastToTechs(JSON.stringify({
        type: 'screenshot',
        clientId: msg.clientId,
        image: msg.image,
        clientName: ws.clientName || 'Cliente'
      }));
      return;
    }
  });

  ws.on('close', () => {
    if (ws.clientId) {
      clients.delete(ws.clientId);
      updateTechs();
    }
  });
});

function updateTechs() {
  const list = Array.from(clients.entries()).map(([id, ws]) => ({ clientId: id, name: ws.clientName }));
  broadcastToTechs(JSON.stringify({ type: 'client_list', clients: list }));
}

function updateSingleTech(ws) {
  const list = Array.from(clients.entries()).map(([id, ws]) => ({ clientId: id, name: ws.clientName }));
  ws.send(JSON.stringify({ type: 'client_list', clients: list }));
}

function broadcastToTechs(payload) {
  wss.clients.forEach((c) => {
    if (c.isTech && c.readyState === WebSocket.OPEN) c.send(payload);
  });
}

// Heartbeat
setInterval(() => {
  wss.clients.forEach((ws) => {
    if (!ws.isAlive) return ws.terminate();
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);

server.listen(PORT, () => {
  console.log(`Servidor a correr em http://localhost:${PORT}`);
  console.log(`WebSocket ativo em ws://localhost:${PORT}`);
});

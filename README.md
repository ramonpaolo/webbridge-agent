# agent-webbridge

🌐 **Universal web frontend for AI agents** — Connect any agent (nanobot, openclaw) via WebSocket with a beautiful chat interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔐 **Secure** — API Key + HMAC signature verification
- 🌐 **Universal** — Works with nanobot, openclaw, and any WebSocket agent
- 💬 **Real-time Chat** — WebSocket-based messaging
- 📎 **File Upload** — Images, documents, and more
- 🎨 **Modern UI** — Clean, dark-themed interface
- 🔄 **Auto-reconnect** — Automatic reconnection on disconnect
- 📱 **Responsive** — Works on desktop and mobile

## Quick Start

### 1. Install

```bash
git clone https://github.com/ramonpaolo/webbridge-agent.git
cd webbridge-agent

# Using pip
pip install -r requirements.txt

# Or using Docker
docker-compose up -d
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required: Your API key (generate a secure random key)
API_KEY=sk_live_abc123def456...

# Required: Your nanobot's webbridge URL
AGENT_WS_URL=ws://localhost:18791

# Optional: HMAC secret for message signatures
HMAC_SECRET=your_hmac_secret_here

# Optional: Display name
AGENT_NAME=My Agent
```

### 3. Run

```bash
uvicorn src.main:app --reload --port 8080
```

Open http://localhost:8080 in your browser.

---

## Nanobot Integration

This guide explains how to integrate **agent-webbridge** with **nanobot**.

### 1. Enable the webbridge channel in nanobot

Edit your `~/.nanobot/config.json`:

```json
{
  "channels": {
    "webbridge": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 18791,
      "hmac_secret": "your_hmac_secret_here",
      "allowed_connections": [
        {
          "api_key": "sk_live_abc123def456...",
          "ip": null
        }
      ]
    }
  }
}
```

### 2. Generate a secure API Key

```bash
# Generate a 32-character random key
openssl rand -hex 16
# Example: 4a7b9c2e1f3d8h6i0jklmnopqrstuvwx
```

### 3. Configure agent-webbridge

In your `.env`:

```env
API_KEY=sk_live_abc123def456...
AGENT_WS_URL=ws://your-nanobot-host:18791
HMAC_SECRET=your_hmac_secret_here
```

### 4. Security Layers

| Layer | Description |
|-------|-------------|
| **API Key** | Validated on WebSocket handshake |
| **IP Whitelist** | Optional per-API-key IP restriction |
| **HMAC Signature** | Optional message integrity verification |

#### IP Whitelist Example

```json
"allowed_connections": [
  {
    "api_key": "sk_live_abc123...",
    "ip": "192.168.1.100"    // Only this IP can use this key
  },
  {
    "api_key": "sk_live_xyz789...",
    "ip": null                 // Any IP can use this key
  }
]
```

#### HMAC Verification

If `hmac_secret` is set, each message must include a valid signature:

```
signature = HMAC-SHA256(secret, f"{timestamp}:{sender_id}:{content}")
```

### 5. Restart nanobot

```bash
# Restart your nanobot service
systemctl --user restart nanobot
# or
pm2 restart nanobot
```

---

## Docker Deployment

### Single Container

```bash
docker run -d \
  --name webbridge-agent \
  -p 8080:8080 \
  -e API_KEY=your_api_key \
  -e AGENT_WS_URL=ws://nanobot:18791 \
  -e HMAC_SECRET=your_secret \
  ramonpaolo/webbridge-agent
```

### Docker Compose (with nanobot)

```yaml
version: '3.8'

services:
  nanobot:
    image: ramonpaolo/nanobot
    ports:
      - "18790:18790"
    volumes:
      - ./nanobot-config:/root/.nanobot
    environment:
      - NANOBOT_CONFIG=/root/.nanobot/config.json

  webbridge-agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - AGENT_WS_URL=ws://nanobot:18791
      - API_KEY=sk_live_your_key
      - HMAC_SECRET=your_hmac_secret
    depends_on:
      - nanobot
```

---

## WebSocket Protocol

### Connection Flow

```
Browser ────(1) auth message───► webbridge
                                     │
                                     ▼
                               (2) validate api_key
                                     │
                                     ▼
                               (3) connect to agent
                                     │
                                     ▼
                               (4) auth to agent
                                     │
                                     ▼
                               (5) bidirectional proxy
```

### Message Format

**Auth message:**
```json
{
  "type": "auth",
  "api_key": "sk_live_..."
}
```

**Send message:**
```json
{
  "type": "message",
  "content": "Hello!",
  "sender_id": "user123",
  "media": [],
  "metadata": {}
}
```

**Receive message:**
```json
{
  "type": "message",
  "content": "Hi there!",
  "chat_id": "session_id",
  "sender_id": "agent"
}
```

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket endpoint |
| POST | `/upload` | File upload |

### Health Check Response

```json
{
  "status": "ok",
  "agent_connected": true,
  "agent_name": "My Agent"
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | - | Your API key |
| `AGENT_WS_URL` | Yes | `ws://localhost:18791` | Agent WebSocket URL |
| `HMAC_SECRET` | No | - | HMAC signature secret |
| `AGENT_NAME` | No | `Agent` | Display name |
| `PORT` | No | `8080` | Server port |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated) |

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development
uvicorn src.main:app --reload --port 8080 --log-level debug

# Run tests
pytest tests/ -v
```

---

## License

MIT © [ramonpaolo](https://github.com/ramonpaolo)

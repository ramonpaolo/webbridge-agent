# agent-webbridge

🌐 **Universal web frontend for AI agents** — Connect any agent (nanobot, openclaw) via WebSocket with a beautiful chat interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Quick Start (5 minutes)

### Step 1: Install the nanobot plugin

```bash
pip install nanobot-webbridge-plugin
```

### Step 2: Configure nanobot

Edit `~/.nanobot/config.json`:

```json
{
  "channels": {
    "webbridge": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 18791,
      "hmac_secret": "",
      "allowed_connections": [
        {
          "api_key": "sk_live_YOUR_API_KEY_HERE",
          "ip": null
        }
      ]
    }
  }
}
```

**Generate your API key:**
```bash
openssl rand -hex 16
```

### Step 3: Restart nanobot

```bash
systemctl --user restart nanobot
# or
pm2 restart nanobot
```

### Step 4: Run agent-webbridge

```bash
git clone https://github.com/ramonpaolo/webbridge-agent.git
cd webbridge-agent
cp .env.example .env
```

Edit `.env`:
```env
API_KEY=sk_live_YOUR_API_KEY_HERE
AGENT_WS_URL=ws://localhost:18791
```

Run:
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
```

### Step 5: Open in browser

Go to **http://localhost:8080**

---

## Architecture

```
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│   agent-webbridge  │◄────────►│   nanobot + plugin  │◄────────►│   AI Agent (LLM)    │
│   (Web Frontend)   │  wss    │   WebBridge Channel │  json    │                     │
│   port 8080        │          │   port 18791        │          │                     │
└─────────────────────┘          └─────────────────────┘          └─────────────────────┘
```

---

## Security

| Layer | Description |
|-------|-------------|
| **API Key** | Required for WebSocket handshake |
| **IP Whitelist** | Optional per-API-key IP restriction |
| **HMAC Signature** | Optional message integrity verification |

### IP Whitelist Example

```json
"allowed_connections": [
  {
    "api_key": "sk_live_...",
    "ip": "203.0.113.50"    // Only this IP can use this key
  }
]
```

### HMAC Signatures

For production, enable HMAC:

1. Set the same `hmac_secret` in both nanobot and agent-webbridge
2. This prevents message tampering in transit

---

## Configuration

### nanobot config.json

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Enable/disable the channel |
| `host` | `0.0.0.0` | Interface to bind |
| `port` | `18791` | WebSocket server port |
| `hmac_secret` | `""` | Secret for HMAC signatures |
| `allowed_connections` | `[]` | List of allowed API keys |

### agent-webbridge .env

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | - | Must match nanobot config |
| `AGENT_WS_URL` | Yes | `ws://localhost:18791` | nanobot WebSocket URL |
| `HMAC_SECRET` | No | - | Must match nanobot config |
| `AGENT_NAME` | No | `Agent` | Display name |
| `PORT` | No | `8080` | HTTP server port |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins |

---

## Docker Deployment

### nanobot with plugin

```bash
# Install plugin in your nanobot container
pip install nanobot-webbridge-plugin

# Configure in config.json
```

### agent-webbridge

```bash
docker run -d \
  --name webbridge-agent \
  -p 8080:8080 \
  -e API_KEY=sk_live_YOUR_API_KEY_HERE \
  -e AGENT_WS_URL=ws://nanobot:18791 \
  ramonpaolo/webbridge-agent
```

### Docker Compose (complete stack)

```yaml
version: '3.8'

services:
  nanobot:
    image: nanobot:latest
    volumes:
      - ./nanobot-config:/root/.nanobot
    command: nanobot run

  webbridge-agent:
    image: ramonpaolo/webbridge-agent
    ports:
      - "8080:8080"
    environment:
      - API_KEY=sk_live_YOUR_API_KEY_HERE
      - AGENT_WS_URL=ws://nanobot:18791
    depends_on:
      - nanobot
```

---

## Features

- 🔐 **Secure** — API Key + HMAC + IP whitelist
- 🌐 **Universal** — Works with any WebSocket agent
- 💬 **Real-time Chat** — WebSocket-based messaging
- 📎 **File Upload** — Images, documents
- 🎨 **Modern UI** — Dark-themed, responsive
- 🔄 **Auto-reconnect** — Automatic reconnection

---

## WebSocket Protocol

### Connection Flow

```
Browser ────(1) auth {api_key}───► agent-webbridge
                                            │
                                            ▼
                                      (2) validate
                                            │
                                            ▼
                                      (3) connect to nanobot
                                            │
                                            ▼
                                      (4) proxy messages
```

### Message Format

**Auth:**
```json
{"type": "auth", "api_key": "sk_live_..."}
```

**Send:**
```json
{
  "type": "message",
  "content": "Hello!",
  "sender_id": "user123",
  "media": [],
  "metadata": {}
}
```

**Receive:**
```json
{
  "type": "message",
  "content": "Hi there!",
  "chat_id": "session_id"
}
```

---

## Troubleshooting

### "Access denied" error

- Verify `api_key` matches exactly in both configs
- Check `allowed_connections` is not empty
- If using IP whitelist, verify your IP

### "Connection refused" error

- Ensure nanobot is running with webbridge enabled
- Check `AGENT_WS_URL` is correct
- Verify ports are not blocked by firewall

### Frontend shows "Disconnected"

- Check browser console for errors
- Verify nanobot is running
- Try hard refresh (Ctrl+Shift+R)

---

## Development

```bash
# Clone
git clone https://github.com/ramonpaolo/agent-webbridge.git
cd agent-webbridge

# Install dependencies
pip install -r requirements.txt

# Run in development
uvicorn src.main:app --reload --port 8080

# Run tests
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Related Projects

| Project | Description |
|---------|-------------|
| [nanobot](https://github.com/ramonpaolo/nanobot) | AI agent framework |
| [nanobot-webbridge-plugin](https://github.com/ramonpaolo/nanobot-webbridge-plugin) | nanobot plugin for WebBridge |

---

## License

MIT © [ramonpaolo](https://github.com/ramonpaolo)

# agent-webbridge

Universal web frontend for AI agents (nanobot, openclaw, etc.)

## Features

- 🌐 **Universal Web Interface** — Connect any agent via WebSocket
- 🔐 **API Key Authentication** — Secure connection with HMAC signatures
- 💬 **Real-time Chat** — WebSocket-based messaging
- 📎 **File Upload** — Send images, documents to the agent
- 🎨 **Modern UI** — Clean, responsive interface

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
uvicorn src.main:app --reload --port 8080
```

Open http://localhost:8080 in your browser.

## Configuration

Set the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_WS_URL` | WebSocket URL to agent | `ws://localhost:18791` |
| `API_KEY` | Your API key | (required) |
| `HMAC_SECRET` | HMAC secret for signatures | (optional) |
| `AGENT_NAME` | Display name for the agent | `Agent` |

## Docker

```bash
docker build -t agent-webbridge .
docker run -p 8080:8080 -e API_KEY=your_key agent-webbridge
```

## Security

- API Key validated on connection
- Optional IP whitelisting (configured on agent side)
- Optional HMAC signatures for message integrity
- CORS configured for your domain only

## Protocol

The webbridge uses JSON over WebSocket:

**Connect (auth):**
```json
{"type": "auth", "api_key": "sk_live_..."}
```

**Send message:**
```json
{"type": "message", "content": "Hello!", "sender_id": "user123"}
```

**Receive message:**
```json
{"type": "message", "content": "Hi there!", "chat_id": "...", "sender_id": "agent"}
```

---

Built with FastAPI + vanilla JS. No heavy frameworks needed.

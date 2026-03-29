# agent-webbridge

🌐 **Universal web frontend for AI agents** — Connect any agent (nanobot, openclaw) via WebSocket with a beautiful chat interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Version](https://img.shields.io/pypi/v/nanobot-webbridge-plugin)](https://pypi.org/project/nanobot-webbridge-plugin/)

---

## Features

- 🔐 **Secure** — API Key + HMAC + IP whitelist
- 🌐 **Universal** — Works with any WebSocket agent (nanobot, openclaw, etc.)
- 💬 **Real-time Chat** — WebSocket-based bidirectional messaging
- 📎 **File Upload** — Images, PDFs, documents
- 🎨 **Modern UI** — Dark-themed, responsive design
- 🔄 **Auto-reconnect** — Automatic reconnection on disconnect
- 📱 **Responsive** — Works on desktop and mobile

---

## Quick Start (5 minutes)

### Prerequisites

- Python 3.10+
- A running agent with WebBridge support (e.g., nanobot with `nanobot-webbridge-plugin`)

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
          "api_key": "sk_live_YOUR_UNIQUE_API_KEY",
          "ip": null
        }
      ]
    }
  }
}
```

### Step 3: Generate a secure API Key

```bash
# Generate a 32-character random key
openssl rand -hex 16

# Example output: 4a7b9c2e1f3d8h6i0jklmnopqrstuvwx
```

> ⚠️ **Important:** Use a unique API key for each deployment. Never share keys between different services.

### Step 4: Restart nanobot

```bash
# If using systemd
systemctl --user restart nanobot

# If using PM2
pm2 restart nanobot

# If running directly
nanobot run
```

### Step 5: Run agent-webbridge

```bash
git clone https://github.com/ramonpaolo/webbridge-agent.git
cd webbridge-agent
cp .env.example .env
```

Edit `.env`:

```env
API_KEY=sk_live_YOUR_UNIQUE_API_KEY
AGENT_WS_URL=ws://localhost:18791
```

Run:

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8080
```

### Step 6: Open in browser

Go to **http://localhost:8080**

---

## Architecture

```
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│   agent-webbridge  │◄────────►│   nanobot + plugin  │◄────────►│   AI Agent (LLM)    │
│   (Web Frontend)   │  wss    │   WebBridge Channel │  json    │                     │
│   port 8080        │          │   port 18791        │          │                     │
└─────────────────────┘          └─────────────────────┘          └─────────────────────┘
         │                                                                              │
         │  User's Browser (HTTPS recommended in production)                            │
         └──────────────────────────────────────────────────────────────────────────────┘
```

---

## Security

This section explains all security measures available.

### Security Layers

| Layer | Required | Description |
|-------|----------|-------------|
| **API Key** | ✅ Yes | Validated during WebSocket handshake |
| **IP Whitelist** | ⚡ Optional | Restrict access by IP address |
| **HMAC Signature** | ⚡ Optional | Message integrity verification |

---

### API Key Authentication

Every WebSocket connection must include a valid API key:

**nanobot config.json:**
```json
"allowed_connections": [
  {
    "api_key": "sk_live_a1b2c3d4e5f6...",
    "ip": null
  }
]
```

**agent-webbridge .env:**
```env
API_KEY=sk_live_a1b2c3d4e5f6...
```

Both keys must **match exactly**.

---

### IP Whitelist

Restrict access to specific IP addresses. This is useful for:

- Enterprise deployments
- Known VPN users
- Internal network access only

**Configuration:**

```json
"allowed_connections": [
  {
    "api_key": "sk_live_...",
    "ip": "192.168.1.100"           // Only this IP can use this key
  },
  {
    "api_key": "sk_live_...",
    "ip": "10.0.0.50"              // Another specific IP
  },
  {
    "api_key": "sk_live_...",
    "ip": null                      // null = Any IP allowed
  }
]
```

**How to find your IP:**

```bash
# Your public IP
curl ifconfig.me

# Your local IP (Linux/macOS)
ip addr show | grep "inet "    # Linux
ifconfig | grep "inet "         # macOS
```

> ⚠️ **Note:** If behind a NAT or proxy, use the IP that nanobot sees (check nanobot logs on connection).

---

### HMAC Signatures (Optional)

HMAC provides message integrity verification. It prevents tampering with messages in transit.

**Enable HMAC:**

1. Set the same `hmac_secret` in both configs:

```json
// nanobot config.json
"webbridge": {
  "hmac_secret": "your_secure_hmac_secret_here"
}
```

```env
# agent-webbridge .env
HMAC_SECRET=your_secure_hmac_secret_here
```

2. Messages will include a signature verified by both sides

**How it works:**

```
signature = HMAC-SHA256(secret, "{timestamp}:{sender_id}:{content}")
```

Messages with timestamps older than 5 minutes are rejected (replay attack protection).

---

### Production Security Checklist

- [ ] Use HTTPS (reverse proxy with nginx/Caddy)
- [ ] Use strong, unique API keys
- [ ] Enable IP whitelist if possible
- [ ] Enable HMAC signatures
- [ ] Keep `hmac_secret` private
- [ ] Use firewall rules to restrict access
- [ ] Monitor logs for unauthorized access attempts

---

## Configuration Reference

### nanobot config.json

| Setting | Type | Default | Required | Description |
|---------|------|---------|----------|-------------|
| `enabled` | boolean | `false` | ✅ Yes | Enable/disable the channel |
| `host` | string | `0.0.0.0` | No | Interface to bind (use `127.0.0.1` for local only) |
| `port` | integer | `18791` | No | WebSocket server port |
| `hmac_secret` | string | `""` | No | Secret for HMAC signatures |
| `allowed_connections` | array | `[]` | ✅ Yes | List of allowed API keys |

**Example with all options:**

```json
{
  "channels": {
    "webbridge": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 18791,
      "hmac_secret": "super_secure_secret_123",
      "allowed_connections": [
        {
          "api_key": "sk_live_prod_key_123",
          "ip": "203.0.113.50"
        },
        {
          "api_key": "sk_live_dev_key_456",
          "ip": null
        }
      ]
    }
  }
}
```

---

### agent-webbridge .env

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | ✅ Yes | - | Must match nanobot config exactly |
| `AGENT_WS_URL` | ✅ Yes | `ws://localhost:18791` | nanobot WebSocket URL |
| `HMAC_SECRET` | ⚡ Optional | - | Must match nanobot hmac_secret |
| `AGENT_NAME` | No | `Agent` | Display name for the bot |
| `PORT` | No | `8080` | HTTP server port |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated) |

**Example .env:**

```env
API_KEY=sk_live_prod_key_123
AGENT_WS_URL=ws://your-nanobot-server:18791
HMAC_SECRET=super_secure_secret_123
AGENT_NAME=Nanobot Assistant
PORT=8080
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## Docker Deployment

### Single Container

```bash
docker run -d \
  --name webbridge-agent \
  -p 8080:8080 \
  -e API_KEY=sk_live_YOUR_KEY \
  -e AGENT_WS_URL=ws://nanobot:18791 \
  -e HMAC_SECRET=your_secret \
  -e AGENT_NAME="Production Bot" \
  ramonpaolo/webbridge-agent
```

### Docker Compose (Complete Stack)

```yaml
version: '3.8'

services:
  nanobot:
    image: nanobot:latest
    volumes:
      - ./nanobot-config:/root/.nanobot
    ports:
      - "18790:18790"  # Gateway API
    command: nanobot run

  webbridge-agent:
    image: ramonpaolo/webbridge-agent
    ports:
      - "8080:8080"
    environment:
      - API_KEY=sk_live_YOUR_KEY
      - AGENT_WS_URL=ws://nanobot:18791
      - HMAC_SECRET=your_secret
      - AGENT_NAME="Production Bot"
      - ALLOWED_ORIGINS=https://yourdomain.com
    depends_on:
      - nanobot
    restart: unless-stopped
```

### Production with Nginx (HTTPS)

```nginx
server {
    listen 443 ssl;
    server_name webbridge.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

---

## WebSocket Protocol

### Connection Flow

```
Browser                     agent-webbridge                    nanobot
   │                             │                               │
   │  1. Connect to /ws          │                               │
   │───────────────────────────►│                               │
   │                             │                               │
   │  2. Send auth               │  3. Validate API key           │
   │  {type: "auth",             │──────────────────────────────►│
   │   api_key: "..."}           │                               │
   │                             │                               │
   │  4. auth_success            │  5. Connect & auth            │
   │◄───────────────────────────│──────────────────────────────►│
   │                             │                               │
   │  6. Send message            │  7. Forward message           │
   │  {type: "message",          │──────────────────────────────►│
   │   content: "..."}          │                               │
   │                             │                               │
   │                             │  8. Process & respond         │
   │  9. Receive response       │◄──────────────────────────────│
   │◄───────────────────────────│                               │
```

### Message Formats

**Auth Request:**
```json
{
  "type": "auth",
  "api_key": "sk_live_..."
}
```

**Auth Success:**
```json
{
  "type": "auth_success",
  "session_id": "abc123..."
}
```

**Send Message:**
```json
{
  "type": "message",
  "content": "Hello!",
  "sender_id": "user_identifier",
  "media": ["/uploads/image.png"],
  "metadata": {
    "timestamp": 1743216000000
  }
}
```

**Receive Message:**
```json
{
  "type": "message",
  "content": "Hello! How can I help?",
  "chat_id": "session_id",
  "media": []
}
```

**Error:**
```json
{
  "type": "error",
  "error": "Unauthorized"
}
```

---

## Troubleshooting

### "Access denied" error

1. **Check API key match:**
   ```bash
   # In nanobot config.json
   grep api_key ~/.nanobot/config.json
   
   # In agent-webbridge .env
   grep API_KEY .env
   ```
   
   Both must be **identical**.

2. **Check allowed_connections is not empty:**
   ```json
   "allowed_connections": [
     {
       "api_key": "your_key",
       "ip": null
     }
   ]
   ```

3. **If using IP whitelist:**
   - Check your IP with: `curl ifconfig.me`
   - Verify it matches the configured IP exactly
   - Remember: `null` means any IP is allowed

### "Connection refused" error

1. **Verify nanobot is running:**
   ```bash
   systemctl --user status nanobot
   # or
   pm2 status nanobot
   ```

2. **Check AGENT_WS_URL is correct:**
   ```
   AGENT_WS_URL=ws://localhost:18791  # For local
   AGENT_WS_URL=ws://192.168.1.100:18791  # For remote
   ```

3. **Check firewall:**
   ```bash
   # Allow port 18791
   sudo ufw allow 18791
   ```

### "Connection timeout" error

1. **Check nanobot webbridge is enabled:**
   ```json
   "webbridge": {
     "enabled": true  // Must be true
   }
   ```

2. **Restart nanobot:**
   ```bash
   systemctl --user restart nanobot
   ```

### Frontend shows "Disconnected"

1. Check browser console (F12) for errors
2. Verify nanobot is running
3. Try hard refresh: `Ctrl+Shift+R` (or `Cmd+Shift+R`)
4. Check browser network tab for WebSocket connection status

### Messages not being received by agent

1. Check nanobot logs for message processing
2. Verify agent is configured to respond
3. Check if agent has valid API key for the LLM provider

---

## Environment Examples

### Development (Local)

```env
API_KEY=sk_live_dev_local_key
AGENT_WS_URL=ws://localhost:18791
HMAC_SECRET=
AGENT_NAME=Local Dev Bot
PORT=8080
ALLOWED_ORIGINS=*
```

### Staging

```env
API_KEY=sk_live_staging_key
AGENT_WS_URL=ws://staging-nanobot.internal:18791
HMAC_SECRET=staging_hmac_secret
AGENT_NAME=Staging Bot
PORT=8080
ALLOWED_ORIGINS=https://staging.yourdomain.com
```

### Production

```env
API_KEY=sk_live_prod_secure_key
AGENT_WS_URL=ws://nanobot.internal:18791
HMAC_SECRET=prod_secure_hmac_secret
AGENT_NAME=Production Assistant
PORT=8080
ALLOWED_ORIGINS=https://app.yourdomain.com
```

---

## Development

```bash
# Clone the repository
git clone https://github.com/ramonpaolo/agent-webbridge.git
cd agent-webbridge

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt

# Run in development mode
uvicorn src.main:app --reload --port 8080 --log-level debug

# Run tests
pytest tests/ -v

# Run specific test type
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/security/ -v
```

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI (HTML) |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket endpoint |
| POST | `/upload` | File upload |

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "ok",
  "agent_connected": true,
  "agent_name": "My Agent"
}
```

### File Upload

```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@image.png"
```

Response:
```json
{
  "files": ["/uploads/abc123.png"]
}
```

---

## Related Projects

| Project | Description | Links |
|---------|-------------|-------|
| **nanobot** | AI agent framework | [GitHub](https://github.com/ramonpaolo/nanobot) |
| **nanobot-webbridge-plugin** | Plugin for nanobot | [GitHub](https://github.com/ramonpaolo/nanobot-webbridge-plugin) • [PyPI](https://pypi.org/project/nanobot-webbridge-plugin/) |

---

## License

MIT © [ramonpaolo](https://github.com/ramonpaolo)

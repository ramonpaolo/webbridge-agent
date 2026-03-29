"""
agent-webbridge — Universal web frontend for AI agents.

This FastAPI app serves as a bridge between a web browser and the agent's
webbridge channel. It handles:
- Serving the static web UI
- WebSocket connections from browsers
- Proxying messages to/from the agent via WebSocket with streaming support
"""

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

# Note: Logging goes to stderr by default (container-compatible)

# Load environment from .env file
from dotenv import load_dotenv
load_dotenv()

# Load environment
AGENT_WS_URL = os.getenv("AGENT_WS_URL", "ws://nanobot:18791")
API_KEY = os.getenv("API_KEY", "")
HMAC_SECRET = os.getenv("HMAC_SECRET", "")
AGENT_NAME = os.getenv("AGENT_NAME", "Agent")
PORT = int(os.getenv("PORT", "8080"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Session storage (in-memory for simplicity)
# In production, use Redis or a database
connected_browsers: dict[str, list[WebSocket]] = {}

# Initialize FastAPI
app = FastAPI(title="agent-webbridge", version="1.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="src/static"), name="static")


def verify_hmac(data: dict) -> bool:
    """Verify HMAC signature on a message."""
    if not HMAC_SECRET:
        return True

    signature = data.get("signature", "")
    timestamp = data.get("timestamp", 0)
    content = data.get("content", "")
    sender_id = data.get("sender_id", "")

    if not signature or not timestamp:
        return False

    current_time = int(time.time())
    if abs(current_time - timestamp) > 300:
        return False

    message = f"{timestamp}:{sender_id}:{content}"
    expected = hmac.new(
        HMAC_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    return secrets.compare_digest(signature, expected)


def create_signature(sender_id: str, content: str) -> tuple[int, str]:
    """Create HMAC signature for a message."""
    timestamp = int(time.time())
    message = f"{timestamp}:{sender_id}:{content}"
    signature = hmac.new(
        HMAC_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return timestamp, signature


class Message(BaseModel):
    """Incoming message from browser."""

    type: str = "message"
    content: str = ""
    sender_id: str = "anonymous"
    media: list[str] = []
    metadata: dict[str, Any] = {}


@app.get("/")
async def root():
    """Serve the main web UI."""
    return FileResponse("src/static/index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent_connected": False,  # Would need to track this
        "agent_name": AGENT_NAME,
        "version": "1.1.0",
        "streaming": True,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for browser connections.

    Protocol:
    1. Browser connects
    2. Browser sends auth message: {"type": "auth", "api_key": "..."}
    3. Server validates and connects to agent WebSocket
    4. Messages are proxied bidirectionally (with streaming support)
    
    Streaming message types from agent:
    - "stream_start": Streaming is beginning
    - "chunk": A partial content chunk
    - "message": Final complete message
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info("Browser connected from {}", client_ip)

    await websocket.accept()

    agent_ws = None
    session_id = None

    try:
        # Wait for auth
        auth_data = await websocket.receive_text()
        try:
            auth = json.loads(auth_data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "error": "Invalid JSON"})
            await websocket.close(4002)
            return

        if auth.get("type") != "auth":
            await websocket.send_json(
                {"type": "error", "error": "Expected auth message"}
            )
            await websocket.close(4003)
            return

        # Validate API key
        if auth.get("api_key") != API_KEY:
            logger.warning("Invalid API key from {}", client_ip)
            await websocket.send_json({"type": "error", "error": "Invalid API key"})
            await websocket.close(4001)
            return

        session_id = secrets.token_urlsafe(16)
        logger.info("Browser authenticated: session={}", session_id)
        await websocket.send_json({"type": "auth_success", "session_id": session_id})

        # Connect to agent
        import websockets

        try:
            agent_ws = await asyncio.wait_for(
                websockets.connect(AGENT_WS_URL), timeout=10
            )
            logger.info("Connected to agent at {}", AGENT_WS_URL)

            # Send auth to agent
            await agent_ws.send(json.dumps({"type": "auth", "api_key": API_KEY}))

            # Wait for agent auth response
            agent_auth = await asyncio.wait_for(agent_ws.recv(), timeout=10)
            agent_response = json.loads(agent_auth)

            if agent_response.get("type") != "auth_success":
                logger.error("Agent auth failed: {}", agent_response)
                await websocket.send_json(
                    {"type": "error", "error": "Agent authentication failed"}
                )
                await websocket.close(5001)
                return

            logger.info("Agent authenticated successfully")

        except asyncio.TimeoutError:
            logger.error("Timeout connecting to agent")
            await websocket.send_json(
                {"type": "error", "error": "Agent connection timeout"}
            )
            await websocket.close(5002)
            return
        except Exception as e:
            logger.error("Failed to connect to agent: {}", e)
            await websocket.send_json(
                {"type": "error", "error": f"Agent connection failed: {e}"}
            )
            await websocket.close(5003)
            return

        # Bidirectional message proxy with streaming support
        async def proxy_to_agent():
            """Forward messages from browser to agent."""
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)

                    # Add HMAC signature if configured
                    if HMAC_SECRET and msg.get("type") == "message":
                        timestamp, signature = create_signature(
                            msg.get("sender_id", "anonymous"), msg.get("content", "")
                        )
                        msg["timestamp"] = timestamp
                        msg["signature"] = signature

                    await agent_ws.send(data)

            except WebSocketDisconnect:
                logger.info("Browser disconnected, closing agent connection")
            except Exception as e:
                logger.error("Error proxying to agent: {}", e)
            finally:
                if agent_ws:
                    await agent_ws.close()

        async def proxy_to_browser():
            """Forward messages from agent to browser, with streaming support."""
            try:
                async for data in agent_ws:
                    # Forward all streaming messages directly to browser
                    # The frontend will handle rendering
                    await websocket.send_text(data)
            except websockets.exceptions.ConnectionClosed:
                logger.info("Agent disconnected")
            except Exception as e:
                logger.error("Error proxying to browser: {}", e)

        # Run both proxies concurrently
        await asyncio.gather(proxy_to_agent(), proxy_to_browser())

    except WebSocketDisconnect:
        logger.info("Browser {} disconnected", client_ip)
    except Exception as e:
        logger.error("WebSocket error: {}", e)
    finally:
        if agent_ws:
            try:
                await agent_ws.close()
            except:
                pass
        logger.info("Session {} closed", session_id or "unknown")


@app.post("/upload")
async def upload_file(request: Request):
    """
    Handle file uploads via HTTP (legacy - WebSocket upload preferred).

    Files are temporarily stored and their paths are returned
    to be sent as media attachments in messages.
    """
    form = await request.form()
    files = []

    # Use absolute path from app directory
    upload_dir = Path(__file__).parent / "static" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for field_name, file in form.items():
        if hasattr(file, "filename") and file.filename:
            # Generate unique filename
            ext = Path(file.filename).suffix
            unique_name = f"{secrets.token_urlsafe(16)}{ext}"
            file_path = upload_dir / unique_name

            # Save file
            content = await file.read()
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            files.append(f"/uploads/{unique_name}")

    return {"files": files}


@app.post("/api/send")
async def send_message(message: Message):
    """
    HTTP fallback for sending messages (alternative to WebSocket).

    Requires the same API key validation.
    """
    if message.sender_id != API_KEY:
        # In a real app, you'd validate against the session
        return {"error": "Unauthorized"}, 401

    # This would need to track active sessions
    # For now, this is a placeholder for HTTP-only mode
    return {"error": "Use WebSocket for messaging"}, 501


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

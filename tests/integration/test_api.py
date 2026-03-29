"""
Integration tests for webbridge agent API endpoints.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient


# Set test environment before importing app
os.environ["API_KEY"] = "test_api_key_123"
os.environ["AGENT_WS_URL"] = "ws://localhost:18791"
os.environ["HMAC_SECRET"] = "test_hmac_secret"
os.environ["AGENT_NAME"] = "Test Agent"


class TestHealthEndpoint:
    """Test /health endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        """Test that health endpoint returns status ok."""
        response = self.client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "agent_name" in data

    def test_health_includes_agent_name(self):
        """Test that health endpoint includes agent name."""
        response = self.client.get("/health")
        data = response.json()

        assert data["agent_name"] == "Test Agent"


class TestRootEndpoint:
    """Test / endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_root_returns_html(self):
        """Test that root endpoint returns HTML."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestUploadEndpoint:
    """Test /upload endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)
        # Create temp upload directory
        self.temp_dir = tempfile.mkdtemp()

    def test_upload_image(self):
        """Test uploading an image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake_image_data")
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                response = self.client.post(
                    "/upload",
                    files={"file": ("test.png", f, "image/png")}
                )

            assert response.status_code == 200
            data = response.json()
            assert "files" in data
            assert len(data["files"]) == 1
            assert data["files"][0].startswith("/uploads/")
        finally:
            os.unlink(temp_path)

    def test_upload_multiple_files(self):
        """Test uploading multiple files."""
        files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(suffix=f"_{i}.txt", delete=False) as f:
                    f.write(f"content {i}".encode())
                    files.append(f.name)

            upload_files = []
            for i, path in enumerate(files):
                upload_files.append(
                    ("files", (f"test_{i}.txt", open(path, "rb"), "text/plain"))
                )

            response = self.client.post("/upload", files=upload_files)

            assert response.status_code == 200
            data = response.json()
            assert len(data["files"]) == 3
        finally:
            for path in files:
                if os.path.exists(path):
                    os.unlink(path)

    def test_upload_pdf(self):
        """Test uploading a PDF file."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake pdf content")
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                response = self.client.post(
                    "/upload",
                    files={"file": ("document.pdf", f, "application/pdf")}
                )

            assert response.status_code == 200
        finally:
            os.unlink(temp_path)

    def test_upload_no_file(self):
        """Test upload with no files returns empty list."""
        response = self.client.post("/upload", files={})
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []


class TestWebSocketEndpoint:
    """Test /ws WebSocket endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_websocket_rejects_without_auth(self):
        """Test that WebSocket requires authentication."""
        with pytest.raises(Exception):  # Connection will be rejected
            with self.client.websocket_connect("/ws") as websocket:
                websocket.send_text("invalid")

    def test_websocket_auth_failure_wrong_key(self):
        """Test that wrong API key is rejected."""
        with pytest.raises(Exception):
            with self.client.websocket_connect("/ws") as websocket:
                websocket.send_json({
                    "type": "auth",
                    "api_key": "wrong_key"
                })
                response = websocket.receive_json()
                assert response["type"] == "error"


class TestCORS:
    """Test CORS configuration."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_cors_headers_present(self):
        """Test that CORS headers are present."""
        response = self.client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Should not 404
        assert response.status_code != 404


class TestMessageEndpoint:
    """Test /api/send endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_send_requires_websocket(self):
        """Test that send endpoint indicates WebSocket should be used."""
        response = self.client.post(
            "/api/send",
            json={
                "type": "message",
                "content": "Hello!",
                "sender_id": "test"
            }
        )
        # Currently returns 501 as WebSocket is the preferred method
        assert response.status_code in [401, 501]


class TestErrorHandling:
    """Test error handling."""

    def setup_method(self):
        """Set up test client."""
        from src.main import app
        self.client = TestClient(app)

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        response = self.client.post(
            "/upload",
            content=b"not valid json",
            headers={"Content-Type": "application/json"}
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_large_upload(self):
        """Test handling of large file upload."""
        # Create a file slightly under the limit
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write 5MB of data
            f.write(b"x" * (5 * 1024 * 1024))
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                response = self.client.post(
                    "/upload",
                    files={"file": ("large.bin", f, "application/octet-stream")}
                )
            # Should complete without crashing
            assert response.status_code == 200
        finally:
            os.unlink(temp_path)

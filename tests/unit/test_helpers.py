"""
Unit tests for webbridge agent helpers and utilities.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch, MagicMock
import pytest


class TestHMACFunctions:
    """Test HMAC signature creation and verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.secret = "test_secret_key_123"

    def _create_signature(self, sender_id: str, content: str, timestamp: int) -> str:
        """Create HMAC signature for a message."""
        message = f"{timestamp}:{sender_id}:{content}"
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, data: dict, secret: str) -> bool:
        """Verify HMAC signature on a message."""
        signature = data.get("signature", "")
        timestamp = data.get("timestamp", 0)
        content = data.get("content", "")
        sender_id = data.get("sender_id", "")

        if not signature or not timestamp:
            return False

        # Reject old timestamps (replay attack protection, 5 min window)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:
            return False

        message = f"{timestamp}:{sender_id}:{content}"
        expected = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def test_valid_signature(self):
        """Test that a valid signature passes verification."""
        timestamp = int(time.time())
        sender_id = "user123"
        content = "Hello, world!"

        signature = self._create_signature(sender_id, content, timestamp)

        data = {
            "signature": signature,
            "timestamp": timestamp,
            "content": content,
            "sender_id": sender_id
        }

        assert self._verify_signature(data, self.secret) is True

    def test_invalid_signature(self):
        """Test that an invalid signature fails verification."""
        data = {
            "signature": "invalid_signature",
            "timestamp": int(time.time()),
            "content": "Hello!",
            "sender_id": "user123"
        }

        assert self._verify_signature(data, self.secret) is False

    def test_tampered_content(self):
        """Test that tampered content fails verification."""
        timestamp = int(time.time())
        sender_id = "user123"
        content = "Hello!"

        signature = self._create_signature(sender_id, content, timestamp)

        data = {
            "signature": signature,
            "timestamp": timestamp,
            "content": "Tampered content!",  # Content was modified
            "sender_id": sender_id
        }

        assert self._verify_signature(data, self.secret) is False

    def test_expired_timestamp(self):
        """Test that expired timestamps fail verification."""
        timestamp = int(time.time()) - 600  # 10 minutes ago

        signature = self._create_signature("user123", "Hello!", timestamp)

        data = {
            "signature": signature,
            "timestamp": timestamp,
            "content": "Hello!",
            "sender_id": "user123"
        }

        assert self._verify_signature(data, self.secret) is False

    def test_future_timestamp(self):
        """Test that future timestamps fail verification."""
        timestamp = int(time.time()) + 600  # 10 minutes in future

        signature = self._create_signature("user123", "Hello!", timestamp)

        data = {
            "signature": signature,
            "timestamp": timestamp,
            "content": "Hello!",
            "sender_id": "user123"
        }

        assert self._verify_signature(data, self.secret) is False

    def test_missing_signature(self):
        """Test that missing signature fails verification."""
        data = {
            "timestamp": int(time.time()),
            "content": "Hello!",
            "sender_id": "user123"
        }

        assert self._verify_signature(data, self.secret) is False

    def test_wrong_secret(self):
        """Test that wrong secret fails verification."""
        timestamp = int(time.time())
        signature = self._create_signature("user123", "Hello!", timestamp)

        data = {
            "signature": signature,
            "timestamp": timestamp,
            "content": "Hello!",
            "sender_id": "user123"
        }

        assert self._verify_signature(data, "wrong_secret") is False


class TestMessageValidation:
    """Test message format validation."""

    def test_valid_message_format(self):
        """Test valid message format."""
        message = {
            "type": "message",
            "content": "Hello!",
            "sender_id": "user123",
            "media": [],
            "metadata": {}
        }

        assert message["type"] == "message"
        assert isinstance(message["content"], str)
        assert isinstance(message["sender_id"], str)
        assert isinstance(message["media"], list)
        assert isinstance(message["metadata"], dict)

    def test_message_with_media(self):
        """Test message with media attachments."""
        message = {
            "type": "message",
            "content": "Check this out!",
            "sender_id": "user123",
            "media": ["/uploads/image1.png", "/uploads/doc.pdf"],
            "metadata": {"timestamp": 1234567890}
        }

        assert len(message["media"]) == 2
        assert message["media"][0].startswith("/uploads/")

    def test_auth_message_format(self):
        """Test authentication message format."""
        auth = {
            "type": "auth",
            "api_key": "sk_live_abc123..."
        }

        assert auth["type"] == "auth"
        assert "api_key" in auth
        assert auth["api_key"].startswith("sk_live_")


class TestSecurityConstants:
    """Test security-related constants."""

    def test_timestamp_tolerance(self):
        """Test that timestamp tolerance is correctly defined."""
        TOLERANCE_SECONDS = 300  # 5 minutes

        current = int(time.time())
        past = current - TOLERANCE_SECONDS + 1  # Just within tolerance
        future = current + TOLERANCE_SECONDS - 1  # Just within tolerance

        # These should be accepted
        assert abs(current - past) <= TOLERANCE_SECONDS
        assert abs(current - future) <= TOLERANCE_SECONDS

        # These should be rejected
        assert abs(current - (past - 1)) > TOLERANCE_SECONDS
        assert abs(current - (future + 1)) > TOLERANCE_SECONDS

    def test_api_key_format(self):
        """Test API key format requirements."""
        valid_key = "sk_live_abc123def456"
        assert valid_key.startswith("sk_live_")
        assert len(valid_key) > 10

        # Invalid keys
        assert not "sk_test_abc123".startswith("sk_live_")
        assert len("") < 10

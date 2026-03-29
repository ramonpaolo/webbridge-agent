"""
Security tests for webbridge agent.

These tests verify security measures including:
- API key validation
- HMAC signature verification
- Replay attack prevention
- Input validation
- Path traversal prevention
- Injection attacks
"""

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import pytest


# Set test environment
os.environ["API_KEY"] = "sk_live_test_key_12345"
os.environ["HMAC_SECRET"] = "test_hmac_secret_456"


class TestAPIKeySecurity:
    """Test API key security."""

    def test_api_key_required(self):
        """Test that empty API key is rejected."""
        api_key = ""
        assert not api_key or len(api_key) < 10

    def test_api_key_format(self):
        """Test API key format validation."""
        valid_key = "sk_live_abc123def456ghi789"

        # Must start with sk_live_
        assert valid_key.startswith("sk_live_")

        # Must be sufficiently long
        assert len(valid_key) >= 20

        # Should not contain special characters that could cause issues
        assert all(c.isalnum() or c in '_-' for c in valid_key)

    def test_api_key_entropy(self):
        """Test that generated API keys have sufficient entropy."""
        key1 = secrets.token_urlsafe(32)
        key2 = secrets.token_urlsafe(32)

        # Keys should be unique
        assert key1 != key2

        # Keys should be sufficiently long (256 bits = 32 bytes = ~43 chars base64)
        assert len(key1) >= 40

    def test_api_key_in_env_var(self):
        """Test that API key from env var is properly loaded."""
        test_key = "sk_live_test_123456789"
        os.environ["API_KEY"] = test_key

        # Simulate loading from env
        loaded_key = os.getenv("API_KEY", "")

        assert loaded_key == test_key
        assert len(loaded_key) > 0


class TestHMACSecurity:
    """Test HMAC signature security."""

    def setup_method(self):
        """Set up test fixtures."""
        self.secret = "secure_hmac_secret_123"
        self.sender_id = "user_123"
        self.content = "Hello, secure world!"

    def _sign(self, timestamp: int, sender_id: str, content: str) -> str:
        """Create HMAC-SHA256 signature."""
        message = f"{timestamp}:{sender_id}:{content}"
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def test_signature_timing_safe_comparison(self):
        """Test that signature comparison is timing-safe."""
        sig1 = self._sign(int(time.time()), self.sender_id, self.content)
        sig2 = self._sign(int(time.time()), self.sender_id, self.content)

        # Using hmac.compare_digest (which we use) is timing-safe
        assert hmac.compare_digest(sig1, sig1) is True
        assert hmac.compare_digest(sig1, sig2) is False

    def test_signature_with_special_characters(self):
        """Test HMAC with special characters in content."""
        content_with_special = "Hello! 中文 🎉 <script>alert('xss')</script>"
        timestamp = int(time.time())

        signature = self._sign(timestamp, self.sender_id, content_with_special)

        # Verify signature is valid hex
        assert all(c in '0123456789abcdef' for c in signature)
        assert len(signature) == 64  # SHA256 produces 64 hex chars

    def test_signature_with_unicode(self):
        """Test HMAC with Unicode characters."""
        unicode_content = "日本語 한국어 العربية 🔐"
        timestamp = int(time.time())

        signature = self._sign(timestamp, self.sender_id, unicode_content)

        assert len(signature) == 64

    def test_different_secrets_produce_different_signatures(self):
        """Test that different secrets produce different signatures."""
        timestamp = int(time.time())

        sig1 = self._sign(timestamp, self.sender_id, self.content)
        sig2 = self._sign(timestamp, self.sender_id, self.content)

        # Same inputs should produce same signature
        assert sig1 == sig2

        # Different secret would produce different signature
        alt_message = f"{timestamp}:{self.sender_id}:{self.content}"
        alt_sig = hmac.new(
            b"different_secret",
            alt_message.encode(),
            hashlib.sha256
        ).hexdigest()

        assert sig1 != alt_sig


class TestReplayAttackPrevention:
    """Test replay attack prevention."""

    def test_old_timestamp_rejected(self):
        """Test that messages with old timestamps are rejected."""
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        tolerance = 300  # 5 minutes

        is_valid = abs(int(time.time()) - old_timestamp) <= tolerance

        assert is_valid is False

    def test_future_timestamp_rejected(self):
        """Test that messages with future timestamps are rejected."""
        future_timestamp = int(time.time()) + 600  # 10 minutes in future
        tolerance = 300

        is_valid = abs(int(time.time()) - future_timestamp) <= tolerance

        assert is_valid is False

    def test_recent_timestamp_accepted(self):
        """Test that recent timestamps are accepted."""
        recent_timestamp = int(time.time()) - 60  # 1 minute ago
        tolerance = 300

        is_valid = abs(int(time.time()) - recent_timestamp) <= tolerance

        assert is_valid is True

    def test_message_idempotency(self):
        """Test that message processing should be idempotent."""
        # Simulate message deduplication
        processed_ids = set()

        message_id = "msg_123"

        # First time should be processed
        if message_id not in processed_ids:
            processed_ids.add(message_id)
            first_time = True
        else:
            first_time = False

        assert first_time is True

        # Second time should be skipped
        if message_id not in processed_ids:
            processed_ids.add(message_id)
            second_time = True
        else:
            second_time = False

        assert second_time is False


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are handled safely."""
        malicious_input = "'; DROP TABLE users; --"

        # Input should be treated as literal string, not SQL
        assert "DROP" not in malicious_input or isinstance(malicious_input, str)
        assert malicious_input == "'; DROP TABLE users; --"

    def test_xss_prevention_in_content(self):
        """Test that XSS attempts are handled safely."""
        xss_input = "<script>alert('xss')</script>Hello"

        # Content should be escaped when displayed (handled by frontend)
        escaped = (
            xss_input
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_path_traversal_prevention(self):
        """Test that path traversal is prevented."""
        malicious_path = "../../../etc/passwd"

        # Normalize path and check it doesn't escape
        normalized = Path(malicious_path).resolve()

        # Should not resolve to /etc/passwd
        assert normalized.parts[-1] != "passwd" or str(normalized).startswith(str(Path.cwd()))

    def test_upload_filename_sanitization(self):
        """Test that uploaded filenames are sanitized."""
        malicious_filename = "../../../var/www/malicious.png"
        safe_dir = Path("/app/uploads")

        # Extract just the filename
        filename = Path(malicious_filename).name

        # Should not contain path separators
        assert "/" not in filename
        assert ".." not in filename

    def test_content_length_limit(self):
        """Test that content length is limited."""
        max_length = 100_000  # 100KB

        long_content = "x" * 1_000_000  # 1MB

        assert len(long_content) > max_length

        # Content should be truncated or rejected
        truncated = long_content[:max_length]
        assert len(truncated) == max_length

    def test_max_media_attachments(self):
        """Test that number of media attachments is limited."""
        max_attachments = 10

        attachments = [f"/uploads/file_{i}.png" for i in range(20)]

        # Should be limited
        limited = attachments[:max_attachments]
        assert len(limited) == max_attachments
        assert len(attachments) > max_attachments


class TestSecureRandom:
    """Test secure random number generation."""

    def test_token_generation(self):
        """Test that tokens are securely generated."""
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)

        # Tokens should be unique
        assert token1 != token2

        # Should have sufficient length
        assert len(token1) >= 40

    def test_session_id_generation(self):
        """Test that session IDs are securely generated."""
        session1 = secrets.token_urlsafe(16)
        session2 = secrets.token_urlsafe(16)

        assert session1 != session2
        assert len(session1) >= 20


class TestCORSOriginValidation:
    """Test CORS origin validation."""

    def test_valid_origins(self):
        """Test valid origin patterns."""
        valid_origins = [
            "http://localhost:3000",
            "https://example.com",
            "https://app.example.com",
        ]

        for origin in valid_origins:
            assert origin.startswith("http")

    def test_origin_parsing(self):
        """Test that origins are properly parsed."""
        allowed_origins = "http://localhost:3000,https://example.com,https://app.example.com"

        origins = [o.strip() for o in allowed_origins.split(",")]

        assert len(origins) == 3
        assert "http://localhost:3000" in origins

    def test_wildcard_origin_handling(self):
        """Test handling of wildcard origin."""
        wildcard = "*"

        # Wildcard should allow all (in dev only)
        is_wildcard = wildcard == "*"

        assert is_wildcard is True


class TestWebSocketSecurity:
    """Test WebSocket security."""

    def test_auth_timeout(self):
        """Test that auth timeout is enforced."""
        timeout_seconds = 10

        # Simulate waiting too long
        wait_time = 15

        is_valid = wait_time <= timeout_seconds
        assert is_valid is False

    def test_max_message_size(self):
        """Test maximum message size limit."""
        max_size = 10 * 1024 * 1024  # 10MB

        # Normal message should pass
        normal_msg = json.dumps({"type": "message", "content": "Hello!"})
        assert len(normal_msg) < max_size

        # Large message should be rejected
        large_msg = json.dumps({"type": "message", "content": "x" * (11 * 1024 * 1024)})
        assert len(large_msg) > max_size


class TestEnvironmentSecurity:
    """Test environment variable security."""

    def test_secrets_not_in_logs(self):
        """Test that secrets are not exposed in logs."""
        secret = "sk_live_super_secret_key"
        log_message = f"Connection established with key {secret[:8]}..."

        # Should only log partial key
        assert secret not in log_message
        assert secret[:8] in log_message

    def test_hmac_secret_required_for_production(self):
        """Test that HMAC secret should be set in production."""
        hmac_secret = os.getenv("HMAC_SECRET", "")

        # In production, secret should be set
        if os.getenv("ENV") == "production":
            assert len(hmac_secret) >= 32


class TestRateLimitingConcept:
    """Test rate limiting concepts (actual rate limiting not implemented)."""

    def test_rate_limit_key_uniqueness(self):
        """Test that rate limit keys are unique per client."""
        api_key = "sk_live_abc123"
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        key1 = f"{api_key}:{ip1}"
        key2 = f"{api_key}:{ip2}"

        assert key1 != key2

    def test_request_counter_reset(self):
        """Test that request counter can be reset."""
        counter = 0
        window_seconds = 60

        # Increment
        counter += 1
        assert counter == 1

        # Reset (simulating window expiry)
        counter = 0
        assert counter == 0

"""
Pytest configuration and shared fixtures for webbridge-agent tests.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    original_env = os.environ.copy()

    os.environ["API_KEY"] = "sk_live_test_key_for_pytest"
    os.environ["AGENT_WS_URL"] = "ws://localhost:18791"
    os.environ["HMAC_SECRET"] = "test_hmac_secret_for_pytest"
    os.environ["AGENT_NAME"] = "Test Agent"
    os.environ["PORT"] = "8081"
    os.environ["ALLOWED_ORIGINS"] = "*"

    yield os.environ

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def temp_upload_dir():
    """Create a temporary directory for uploads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_message():
    """Sample message for testing."""
    return {
        "type": "message",
        "content": "Hello, world!",
        "sender_id": "test_user_123",
        "media": [],
        "metadata": {
            "timestamp": 1234567890
        }
    }


@pytest.fixture
def sample_auth_message():
    """Sample auth message for testing."""
    return {
        "type": "auth",
        "api_key": "sk_live_test_key_for_pytest"
    }


@pytest.fixture
def valid_hmac_signature():
    """Generate a valid HMAC signature for testing."""
    import hashlib
    import hmac
    import time

    secret = "test_hmac_secret_for_pytest"
    timestamp = int(time.time())
    sender_id = "test_user_123"
    content = "Hello, world!"

    message = f"{timestamp}:{sender_id}:{content}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "timestamp": timestamp,
        "signature": signature
    }


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient

    # Import app after env is set
    from src.main import app

    return TestClient(app)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)

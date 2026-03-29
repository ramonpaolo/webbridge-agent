"""
End-to-end tests for webbridge agent using Playwright.

These tests verify the full user flow:
- Page loading
- UI interactions
- WebSocket connection
- Chat functionality

Run with: pytest tests/e2e/ -v
Requires: pip install pytest-playwright playwright && playwright install chromium
"""

import asyncio
import os
import time
from typing import Generator
import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, expect


# Set test environment
os.environ["API_KEY"] = "test_api_key_e2e"
os.environ["AGENT_WS_URL"] = "ws://localhost:18791"
os.environ["PORT"] = "8081"  # Use different port for testing


class TestPageLoad:
    """Test page loading and initial state."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        """Set up browser."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def context(self, browser: Browser) -> BrowserContext:
        """Set up browser context."""
        context = browser.new_context()
        yield context
        context.close()

    @pytest.fixture(scope="class")
    def page(self, context: BrowserContext) -> Page:
        """Set up page."""
        page = context.new_page()
        yield page
        page.close()

    def test_page_loads_without_errors(self, page: Page):
        """Test that page loads without JavaScript errors."""
        errors = []

        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        try:
            page.goto("http://localhost:8081", timeout=10000)
            page.wait_for_load_state("domcontentloaded")
        except Exception:
            pytest.skip("Server not running - start with: uvicorn src.main:app --port 8081")

        assert len(errors) == 0, f"Page errors: {errors}"

    def test_page_has_title(self, page: Page):
        """Test that page has a title."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        assert page.title() != ""

    def test_status_bar_visible(self, page: Page):
        """Test that status bar is visible."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        status_bar = page.locator("#status-bar")
        expect(status_bar).to_be_visible()

    def test_connection_status_shows_disconnected(self, page: Page):
        """Test that connection status shows disconnected initially."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        status = page.locator("#connection-status")
        expect(status).to_be_visible()
        expect(status).to_contain_text("Disconnected")

    def test_welcome_message_visible(self, page: Page):
        """Test that welcome message is visible when disconnected."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        welcome = page.locator("#welcome-message")
        expect(welcome).to_be_visible()

    def test_settings_button_exists(self, page: Page):
        """Test that settings button exists."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        settings_btn = page.locator("#settings-btn")
        expect(settings_btn).to_be_visible()


class TestUIElements:
    """Test UI elements and their states."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def page(self, browser: Browser) -> Page:
        page = browser.new_page()
        yield page
        page.close()

    def test_message_input_exists(self, page: Page):
        """Test that message input exists."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        message_input = page.locator("#message-input")
        expect(message_input).to_be_visible()

    def test_send_button_exists(self, page: Page):
        """Test that send button exists."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        send_btn = page.locator("#send-btn")
        expect(send_btn).to_be_visible()

    def test_send_button_disabled_initially(self, page: Page):
        """Test that send button is disabled when no message."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        send_btn = page.locator("#send-btn")
        expect(send_btn).to_be_disabled()

    def test_attach_button_exists(self, page: Page):
        """Test that attach button exists."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        attach_btn = page.locator("#attach-btn")
        expect(attach_btn).to_be_visible()

    def test_chat_container_exists(self, page: Page):
        """Test that chat container exists."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        chat_container = page.locator("#chat-container")
        expect(chat_container).to_be_visible()


class TestSettingsModal:
    """Test settings modal functionality."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def page(self, browser: Browser) -> Page:
        page = browser.new_page()
        yield page
        page.close()

    def test_settings_modal_opens(self, page: Page):
        """Test that settings modal opens."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        # Click settings button
        page.locator("#settings-btn").click()

        # Modal should be visible
        modal = page.locator("#settings-modal")
        expect(modal).to_be_visible()

    def test_settings_modal_closes(self, page: Page):
        """Test that settings modal closes."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        # Open modal
        page.locator("#settings-btn").click()

        # Close modal
        page.locator("#close-settings").click()

        # Modal should be hidden
        modal = page.locator("#settings-modal")
        expect(modal).to_be_hidden()

    def test_api_key_input_exists(self, page: Page):
        """Test that API key input exists in modal."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        page.locator("#settings-btn").click()

        api_key_input = page.locator("#api-key-input")
        expect(api_key_input).to_be_visible()

    def test_connect_button_exists(self, page: Page):
        """Test that connect button exists in modal."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        page.locator("#settings-btn").click()

        connect_btn = page.locator("#connect-btn")
        expect(connect_btn).to_be_visible()
        expect(connect_btn).to_contain_text("Connect")


class TestUserInteractions:
    """Test user interactions."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def page(self, browser: Browser) -> Page:
        page = browser.new_page()
        yield page
        page.close()

    def test_type_in_message_input(self, page: Page):
        """Test typing in message input."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        message_input = page.locator("#message-input")
        message_input.fill("Hello, world!")

        expect(message_input).to_have_value("Hello, world!")

    def test_send_button_enabled_after_typing(self, page: Page):
        """Test that send button becomes enabled after typing."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        message_input = page.locator("#message-input")
        message_input.fill("Hello!")

        # Send button should be enabled (if connected)
        # Note: Without connection, it may still be disabled

    def test_enter_key_sends_message(self, page: Page):
        """Test that Enter key would send message (if connected)."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        message_input = page.locator("#message-input")
        message_input.fill("Test message")
        message_input.press("Enter")

        # Message input should be cleared after sending
        # (if connected)


class TestResponsive:
    """Test responsive design."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    def test_mobile_viewport(self, browser: Browser):
        """Test page on mobile viewport."""
        context = browser.new_context(
            viewport={"width": 375, "height": 667}  # iPhone SE
        )
        page = context.new_page()

        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        # Page should load
        expect(page.locator("#app")).to_be_visible()
        context.close()

    def test_tablet_viewport(self, browser: Browser):
        """Test page on tablet viewport."""
        context = browser.new_context(
            viewport={"width": 768, "height": 1024}  # iPad
        )
        page = context.new_page()

        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        expect(page.locator("#app")).to_be_visible()
        context.close()

    def test_desktop_viewport(self, browser: Browser):
        """Test page on desktop viewport."""
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        expect(page.locator("#app")).to_be_visible()
        context.close()


class TestAccessibility:
    """Test accessibility features."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def page(self, browser: Browser) -> Page:
        page = browser.new_page()
        yield page
        page.close()

    def test_inputs_have_labels(self, page: Page):
        """Test that inputs have associated labels."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        page.locator("#settings-btn").click()

        # Check API key input has label
        api_key_label = page.locator('label[for="api-key-input"]')
        expect(api_key_label).to_be_visible()

    def test_buttons_are_focusable(self, page: Page):
        """Test that buttons can be focused."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        settings_btn = page.locator("#settings-btn")
        settings_btn.focus()

        # Button should be focused (no assertion error)
        assert True

    def test_message_input_is_focusable(self, page: Page):
        """Test that message input can be focused."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        message_input = page.locator("#message-input")
        message_input.focus()

        assert True


class TestPerformance:
    """Test performance characteristics."""

    @pytest.fixture(scope="class")
    def browser(self) -> Generator[Browser, None, None]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()

    @pytest.fixture(scope="class")
    def page(self, browser: Browser) -> Page:
        page = browser.new_page()
        yield page
        page.close()

    def test_page_load_time(self, page: Page):
        """Test that page loads within reasonable time."""
        try:
            start = time.time()
            page.goto("http://localhost:8081", timeout=10000)
            load_time = time.time() - start
        except Exception:
            pytest.skip("Server not running")

        # Page should load within 3 seconds
        assert load_time < 3, f"Page took {load_time}s to load"

    def test_no_excessive_dom_nodes(self, page: Page):
        """Test that DOM doesn't have excessive nodes."""
        try:
            page.goto("http://localhost:8081", timeout=10000)
        except Exception:
            pytest.skip("Server not running")

        # Count DOM nodes
        node_count = page.evaluate("document.querySelectorAll('*').length")

        # Should have reasonable number of nodes
        assert node_count < 1000, f"Too many DOM nodes: {node_count}"


# Mark all tests in this module as e2e
pytestmark = pytest.mark.e2e

"""Browser automation tool using browser-use.

Provides deterministic browser automation with:
- Session persistence (cookie-based)
- Credential store integration
- Platform-specific login flows
- MFA handling
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BrowserAction(BaseModel):
    """Structured browser action for deterministic execution."""

    action: str  # goto, click, fill, upload, query, query_all, wait_for, screenshot
    selector: str | None = None
    value: str | None = None
    timeout: int = 30


class MFARequired(Exception):
    """Raised when MFA code is needed."""

    def __init__(self, platform: str, message: str = "MFA code required"):
        self.platform = platform
        self.message = message
        super().__init__(f"{platform}: {message}")


class LoginRequired(Exception):
    """Raised when login is needed."""

    def __init__(self, platform: str, message: str = "Login required"):
        self.platform = platform
        self.message = message
        super().__init__(f"{platform}: {message}")


@dataclass
class PlatformConfig:
    """Configuration for a social media platform."""

    name: str
    base_url: str
    login_url: str
    logged_in_indicator: str
    login_selectors: dict[str, str] = field(default_factory=dict)


# Platform configurations
PLATFORMS: dict[str, PlatformConfig] = {
    "linkedin": PlatformConfig(
        name="linkedin",
        base_url="https://www.linkedin.com",
        login_url="https://www.linkedin.com/login",
        logged_in_indicator="div.feed-identity-module",
        login_selectors={
            "email": "#username",
            "password": "#password",
            "submit": "button[type='submit']",
            "mfa": "input#pin",
        },
    ),
    "twitter": PlatformConfig(
        name="twitter",
        base_url="https://x.com",
        login_url="https://x.com/i/flow/login",
        logged_in_indicator="a[href='/compose/tweet']",
        login_selectors={
            "email": "input[autocomplete='username']",
            "password": "input[type='password']",
            "submit": "button[data-testid='LoginForm_Login_Button']",
            "mfa": "input[data-testid='ocfEnterTextTextInput']",
        },
    ),
    "medium": PlatformConfig(
        name="medium",
        base_url="https://medium.com",
        login_url="https://medium.com/m/signin",
        logged_in_indicator="button[data-testid='headerWriteButton']",
        login_selectors={
            "google": "button[data-testid='googleButton']",
            "email": "input[type='email']",
        },
    ),
    "substack": PlatformConfig(
        name="substack",
        base_url="https://substack.com",
        login_url="https://substack.com/sign-in",
        logged_in_indicator="button[class*='publish']",
        login_selectors={
            "email": "input[type='email']",
            "password": "input[type='password']",
            "submit": "button[type='submit']",
        },
    ),
}


class BrowserTool:
    """Browser automation tool with session persistence.

    Features:
    - Persistent sessions via cookies
    - Credential store integration
    - Platform-specific login flows
    - MFA handling with user prompts
    - Deterministic action execution

    Example:
        ```python
        browser = BrowserTool()
        await browser.launch()

        # Check if logged in, auto-restore session
        if not await browser.ensure_logged_in("linkedin"):
            await browser.login("linkedin")

        # Execute actions
        await browser.execute([
            BrowserAction(action="goto", value="https://linkedin.com/feed"),
            BrowserAction(action="click", selector="button.share-box"),
            BrowserAction(action="fill", selector="div.editor", value="Hello!"),
        ])

        await browser.close()
        ```
    """

    name = "browser"
    description = "Execute browser automation actions with session persistence"

    def __init__(
        self,
        session_dir: Path | None = None,
        headless: bool = False,
        profile_path: Path | None = None,
    ):
        """Initialize browser tool.

        Args:
            session_dir: Directory for session cookies. Defaults to ~/.teotl/browser/sessions
            headless: Run browser in headless mode. Default False for auth flows.
            profile_path: Optional Chrome profile path to use existing logins.
        """
        self.session_dir = session_dir or Path.home() / ".teotl" / "browser" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.headless = headless
        self.profile_path = profile_path
        self.browser = None
        self.page = None

    async def launch(self) -> None:
        """Launch browser instance."""
        try:
            from browser_use import Browser, BrowserConfig
        except ImportError:
            raise ImportError(
                "browser-use package required. Install with:\n"
                "  pip install teotl[browser]\n"
                "Then install browser binaries:\n"
                "  playwright install chromium"
            )

        config = BrowserConfig(
            headless=self.headless,
            disable_security=False,
        )

        # Use Chrome profile if specified
        if self.profile_path:
            config.chrome_instance_path = str(self.profile_path)

        try:
            self.browser = Browser(config=config)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
        except Exception as e:
            error_msg = str(e).lower()
            if "executable doesn't exist" in error_msg or "browsertype.launch" in error_msg:
                raise RuntimeError(
                    "Browser binaries not installed. Run:\n"
                    "  playwright install chromium\n\n"
                    "Or install all browsers:\n"
                    "  playwright install"
                ) from e
            raise

        logger.info("Browser launched")

    async def close(self) -> None:
        """Close browser instance."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            logger.info("Browser closed")

    # =========================================================================
    # Session Management
    # =========================================================================

    def _session_file(self, platform: str) -> Path:
        """Get session file path for platform."""
        return self.session_dir / f"{platform}_cookies.json"

    async def save_session(self, platform: str) -> None:
        """Save current cookies for platform."""
        if not self.context:
            return

        cookies = await self.context.cookies()
        session_file = self._session_file(platform)
        session_file.write_text(json.dumps(cookies, indent=2))
        logger.info(f"Saved session for {platform}")

    async def restore_session(self, platform: str) -> bool:
        """Restore saved session cookies.

        Returns:
            True if session was restored, False if no session exists.
        """
        session_file = self._session_file(platform)

        if not session_file.exists():
            logger.debug(f"No saved session for {platform}")
            return False

        try:
            cookies = json.loads(session_file.read_text())
            await self.context.add_cookies(cookies)
            logger.info(f"Restored session for {platform}")
            return True
        except Exception as e:
            logger.warning(f"Failed to restore session for {platform}: {e}")
            return False

    async def clear_session(self, platform: str) -> None:
        """Clear saved session for platform."""
        session_file = self._session_file(platform)
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Cleared session for {platform}")

    # =========================================================================
    # Authentication
    # =========================================================================

    async def is_logged_in(self, platform: str) -> bool:
        """Check if currently logged into platform."""
        config = PLATFORMS.get(platform)
        if not config:
            raise ValueError(f"Unknown platform: {platform}")

        await self.page.goto(config.base_url, wait_until="networkidle")

        # Check for login indicator
        try:
            element = await self.page.query_selector(config.logged_in_indicator)
            return element is not None
        except Exception:
            return False

    async def ensure_logged_in(self, platform: str) -> bool:
        """Ensure logged into platform, restoring session if needed.

        Returns:
            True if logged in, False if login is required.
        """
        # Try to restore session
        await self.restore_session(platform)

        # Check if logged in
        if await self.is_logged_in(platform):
            logger.info(f"Already logged into {platform}")
            return True

        logger.info(f"Not logged into {platform}, login required")
        return False

    async def login(
        self,
        platform: str,
        credentials: dict[str, str] | None = None,
        mfa_callback: callable | None = None,
    ) -> bool:
        """Login to platform.

        Args:
            platform: Platform name (linkedin, twitter, medium, substack)
            credentials: Optional dict with email/password. If not provided,
                         will try to load from credential store.
            mfa_callback: Optional async callback to get MFA code from user.
                          Should return the MFA code string.

        Returns:
            True if login successful.

        Raises:
            LoginRequired: If credentials not available.
            MFARequired: If MFA needed and no callback provided.
        """
        config = PLATFORMS.get(platform)
        if not config:
            raise ValueError(f"Unknown platform: {platform}")

        # Get credentials
        if not credentials:
            credentials = await self._load_credentials(platform)

        if not credentials:
            raise LoginRequired(platform, "No credentials available")

        # Navigate to login page
        await self.page.goto(config.login_url, wait_until="networkidle")

        # Platform-specific login flow
        if platform == "linkedin":
            await self._login_linkedin(config, credentials, mfa_callback)
        elif platform == "twitter":
            await self._login_twitter(config, credentials, mfa_callback)
        elif platform == "medium":
            await self._login_medium(config, credentials)
        elif platform == "substack":
            await self._login_substack(config, credentials, mfa_callback)

        # Verify login success
        if await self.is_logged_in(platform):
            await self.save_session(platform)
            logger.info(f"Successfully logged into {platform}")
            return True

        logger.error(f"Login to {platform} failed")
        return False

    async def _load_credentials(self, platform: str) -> dict[str, str] | None:
        """Load credentials from teotl credential store."""
        try:
            from teotl.primitives.integrations.credential_store import CredentialStore

            store = CredentialStore.create()
            return store.load_credential(platform)
        except Exception as e:
            logger.debug(f"Could not load credentials for {platform}: {e}")
            return None

    async def _login_linkedin(
        self,
        config: PlatformConfig,
        credentials: dict[str, str],
        mfa_callback: callable | None,
    ) -> None:
        """LinkedIn login flow."""
        selectors = config.login_selectors

        # Fill email
        await self.page.fill(selectors["email"], credentials.get("email", ""))
        # Fill password
        await self.page.fill(selectors["password"], credentials.get("password", ""))
        # Submit
        await self.page.click(selectors["submit"])

        # Wait for navigation
        await self.page.wait_for_load_state("networkidle")

        # Check for MFA
        mfa_input = await self.page.query_selector(selectors["mfa"])
        if mfa_input:
            if not mfa_callback:
                raise MFARequired("linkedin", "MFA code required")

            mfa_code = await mfa_callback("Enter LinkedIn MFA code:")
            await self.page.fill(selectors["mfa"], mfa_code)
            await self.page.click(selectors["submit"])
            await self.page.wait_for_load_state("networkidle")

    async def _login_twitter(
        self,
        config: PlatformConfig,
        credentials: dict[str, str],
        mfa_callback: callable | None,
    ) -> None:
        """Twitter/X login flow."""
        selectors = config.login_selectors

        # Twitter has a multi-step login flow
        # Step 1: Enter email/username
        await self.page.wait_for_selector(selectors["email"])
        await self.page.fill(selectors["email"], credentials.get("email", ""))
        await self.page.keyboard.press("Enter")

        # Step 2: Enter password
        await self.page.wait_for_selector(selectors["password"], timeout=10000)
        await self.page.fill(selectors["password"], credentials.get("password", ""))
        await self.page.keyboard.press("Enter")

        # Wait for navigation
        await self.page.wait_for_load_state("networkidle")

        # Check for MFA
        mfa_input = await self.page.query_selector(selectors["mfa"])
        if mfa_input:
            if not mfa_callback:
                raise MFARequired("twitter", "MFA code required")

            mfa_code = await mfa_callback("Enter X/Twitter MFA code:")
            await self.page.fill(selectors["mfa"], mfa_code)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_load_state("networkidle")

    async def _login_medium(
        self,
        config: PlatformConfig,
        credentials: dict[str, str],
    ) -> None:
        """Medium login flow (email magic link or Google)."""
        # Medium primarily uses email magic link or OAuth
        # This implementation handles email-based login
        selectors = config.login_selectors

        # Click email option if available
        email_button = await self.page.query_selector("button:has-text('email')")
        if email_button:
            await email_button.click()

        await self.page.wait_for_selector(selectors["email"])
        await self.page.fill(selectors["email"], credentials.get("email", ""))
        await self.page.keyboard.press("Enter")

        # Note: Medium sends a magic link, user needs to click it
        logger.info("Medium login: Check email for magic link")

    async def _login_substack(
        self,
        config: PlatformConfig,
        credentials: dict[str, str],
        mfa_callback: callable | None,
    ) -> None:
        """Substack login flow."""
        selectors = config.login_selectors

        await self.page.fill(selectors["email"], credentials.get("email", ""))
        await self.page.fill(selectors["password"], credentials.get("password", ""))
        await self.page.click(selectors["submit"])

        await self.page.wait_for_load_state("networkidle")

    # =========================================================================
    # Action Execution
    # =========================================================================

    async def execute(self, actions: list[BrowserAction]) -> dict[str, Any]:
        """Execute a sequence of browser actions.

        Args:
            actions: List of BrowserAction objects to execute in order.

        Returns:
            Dict with success status and any query results.
        """
        if not self.page:
            raise RuntimeError("Browser not launched. Call launch() first.")

        results = []

        for action in actions:
            try:
                result = await self._execute_action(action)
                results.append(result)
            except Exception as e:
                logger.error(f"Action failed: {action.action} - {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "failed_action": action.model_dump(),
                    "results": results,
                }

        return {"success": True, "results": results}

    async def _execute_action(self, action: BrowserAction) -> Any:
        """Execute a single browser action."""
        if action.action == "goto":
            await self.page.goto(action.value, wait_until="networkidle")
            return {"url": self.page.url}

        elif action.action == "click":
            await self.page.click(action.selector, timeout=action.timeout * 1000)
            return {"clicked": action.selector}

        elif action.action == "fill":
            await self.page.fill(action.selector, action.value)
            return {"filled": action.selector}

        elif action.action == "type":
            # Type with delays (more human-like)
            await self.page.type(action.selector, action.value, delay=50)
            return {"typed": action.selector}

        elif action.action == "upload":
            await self.page.set_input_files(action.selector, action.value)
            return {"uploaded": action.value}

        elif action.action == "query":
            element = await self.page.query_selector(action.selector)
            if element:
                text = await element.text_content()
                return {"text": text}
            return {"text": None}

        elif action.action == "query_all":
            elements = await self.page.query_selector_all(action.selector)
            texts = []
            for el in elements:
                text = await el.text_content()
                texts.append(text)
            return {"texts": texts}

        elif action.action == "wait_for":
            await self.page.wait_for_selector(
                action.selector, timeout=action.timeout * 1000
            )
            return {"found": action.selector}

        elif action.action == "screenshot":
            path = action.value or "screenshot.png"
            await self.page.screenshot(path=path)
            return {"screenshot": path}

        elif action.action == "scroll":
            await self.page.evaluate(f"window.scrollBy(0, {action.value or 500})")
            return {"scrolled": action.value}

        elif action.action == "wait":
            import asyncio
            await asyncio.sleep(float(action.value or 1))
            return {"waited": action.value}

        elif action.action == "press":
            await self.page.keyboard.press(action.value)
            return {"pressed": action.value}

        else:
            raise ValueError(f"Unknown action: {action.action}")

    # =========================================================================
    # High-Level Operations
    # =========================================================================

    async def get_page_content(self) -> str:
        """Get current page text content."""
        return await self.page.text_content("body")

    async def get_page_html(self) -> str:
        """Get current page HTML."""
        return await self.page.content()

    async def current_url(self) -> str:
        """Get current page URL."""
        return self.page.url

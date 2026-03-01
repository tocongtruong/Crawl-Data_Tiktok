"""
TikTok Service - Lớp bọc TikTokApi cho Flask app.

Quản lý browser Playwright dùng chung (shared browser), tạo session
tạm thời cho mỗi HTTP request với cookie/proxy riêng.
"""

import sys
import os
import asyncio
import logging
from urllib.parse import urlparse
from contextlib import asynccontextmanager

# Thêm thư mục cha vào sys.path để import TikTokApi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from TikTokApi import TikTokApi
from TikTokApi.stealth import stealth_async

logger = logging.getLogger("tiktok_service")


def parse_cookie_string(cookie_str: str) -> dict:
    """
    Parse raw cookie string thành dict.

    Input:  "msToken=xxx; tt_webid=yyy; tt_csrf_token=zzz"
    Output: {"msToken": "xxx", "tt_webid": "yyy", "tt_csrf_token": "zzz"}
    """
    cookies = {}
    if not cookie_str:
        return cookies
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            key, value = pair.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def extract_ms_token(cookies_dict: dict) -> str | None:
    """Trích xuất msToken từ cookies dict."""
    return cookies_dict.get("msToken") or cookies_dict.get("ms_token")


def parse_proxy_string(proxy_str: str) -> dict | None:
    """
    Parse proxy string thành Playwright ProxySettings dict.

    Hỗ trợ format:
        - http://host:port
        - http://user:pass@host:port
        - socks5://user:pass@host:port
    """
    if not proxy_str:
        return None
    proxy_str = proxy_str.strip()
    parsed = urlparse(proxy_str)

    result = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    }
    if parsed.username:
        result["username"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    return result


class TikTokService:
    """
    Service quản lý TikTokApi instance dùng chung cho Flask app.

    - Browser Playwright khởi tạo 1 lần duy nhất khi startup.
    - Mỗi HTTP request tạo session mới (context + page) với cookie/proxy riêng.
    - Dùng xong session thì đóng ngay để giải phóng tài nguyên.
    """

    def __init__(self):
        self.api: TikTokApi = None
        self._initialized = False

    async def init_browser(self):
        """Khởi tạo TikTokApi và browser Playwright."""
        if self._initialized:
            return

        self.api = TikTokApi(logging_level=logging.INFO)
        from playwright.async_api import async_playwright
        self.api.playwright = await async_playwright().start()
        self.api.browser = await self.api.playwright.chromium.launch(
            headless=True,
            args=["--headless=new"],
        )
        self._initialized = True
        logger.info("Playwright browser đã khởi tạo thành công")

    async def shutdown(self):
        """Đóng browser và playwright."""
        if self.api:
            try:
                if self.api.browser:
                    await self.api.browser.close()
                    self.api.browser = None
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            try:
                if self.api.playwright:
                    await self.api.playwright.stop()
                    self.api.playwright = None
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
            self._initialized = False
            logger.info("Playwright browser đã đóng")

    async def _create_session(self, cookies_dict: dict, proxy: dict = None):
        """
        Tạo 1 session Playwright mới với cookie/proxy cho trước.

        Returns:
            (session, session_index): Session vừa tạo và index của nó.
        """
        import random
        from TikTokApi.tiktok import TikTokPlaywrightSession

        ms_token = extract_ms_token(cookies_dict)

        # Chuẩn bị cookies cho Playwright context
        context_cookies = cookies_dict.copy()
        if ms_token:
            context_cookies["msToken"] = ms_token

        # Tạo browser context mới với proxy (nếu có)
        context_options = {}
        context = await self.api.browser.new_context(
            proxy=proxy, **context_options
        )

        # Thêm cookies vào context
        url = "https://www.tiktok.com"
        formatted_cookies = [
            {"name": k, "value": v, "domain": ".tiktok.com", "path": "/"}
            for k, v in context_cookies.items()
            if v is not None
        ]
        await context.add_cookies(formatted_cookies)

        # Tạo page mới và áp dụng stealth
        page = await context.new_page()
        await stealth_async(page)

        # Đăng ký listener TRƯỚC khi goto để capture headers từ request đầu tiên
        request_headers = None

        def handle_request(request):
            nonlocal request_headers
            if request_headers is None:
                request_headers = request.headers

        page.on("request", handle_request)

        try:
            await page.goto(url, timeout=30000)
        except Exception as e:
            logger.warning(f"Lỗi khi truy cập TikTok: {e}")
            try:
                await page.goto("https://www.tiktok.com/foryou", timeout=30000)
            except Exception:
                pass

        if "tiktok" not in page.url:
            try:
                await page.goto("https://www.tiktok.com", timeout=30000)
            except Exception:
                pass

        # Gỡ listener sau khi đã capture
        page.remove_listener("request", handle_request)

        # Set navigation timeout
        page.set_default_navigation_timeout(30000)

        # Mô phỏng di chuột để tránh bot detection
        x, y = random.randint(0, 50), random.randint(0, 50)
        a, b = random.randint(1, 50), random.randint(100, 200)
        await page.mouse.move(x, y)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.mouse.move(a, b)

        # Đảm bảo headers không bao giờ là None
        if request_headers is None:
            logger.debug("Không capture được request headers, dùng empty dict")
            request_headers = {}
        else:
            logger.info(f"Captured {len(request_headers)} request headers")

        # Tạo session object
        session = TikTokPlaywrightSession(
            context=context,
            page=page,
            ms_token=ms_token,
            proxy=proxy,
            headers=request_headers,
            base_url=url,
            is_valid=True,
        )

        # Nếu không có ms_token, thử đọc từ cookie browser
        if ms_token is None:
            await asyncio.sleep(3)
            browser_cookies = await self.api.get_session_cookies(session)
            ms_token = browser_cookies.get("msToken")
            session.ms_token = ms_token
            if ms_token is None:
                logger.warning("Không tìm thấy msToken trong cookies")

        # Thêm session vào danh sách và set params
        self.api.sessions.append(session)
        await self.api._TikTokApi__set_session_params(session)

        session_index = len(self.api.sessions) - 1
        return session, session_index

    async def _cleanup_session(self, session):
        """Đóng và xoá 1 session khỏi danh sách."""
        try:
            if session.page:
                await session.page.close()
        except Exception:
            pass
        try:
            if session.context:
                await session.context.close()
        except Exception:
            pass
        try:
            if session in self.api.sessions:
                self.api.sessions.remove(session)
        except Exception:
            pass

    @asynccontextmanager
    async def session_context(self, cookie_str: str, proxy_str: str = None):
        """
        Context manager tạo session tạm thời cho 1 request.

        Usage:
            async with service.session_context(cookie_str, proxy_str) as (session, idx):
                # dùng session_index=idx khi gọi API
        """
        cookies_dict = parse_cookie_string(cookie_str)
        proxy = parse_proxy_string(proxy_str)
        session, idx = await self._create_session(cookies_dict, proxy)
        try:
            yield session, idx
        finally:
            await self._cleanup_session(session)


# Singleton instance
service = TikTokService()

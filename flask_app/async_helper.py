"""
Async Helper - Quản lý event loop chạy async code từ Flask sync views.

Tạo 1 background daemon thread chạy asyncio event loop duy nhất.
Playwright browser sống trên loop này, tránh khởi tạo lại mỗi request.
"""

import asyncio
import threading
from typing import Any, Coroutine

_loop: asyncio.AbstractEventLoop = None
_thread: threading.Thread = None


def _start_background_loop(loop: asyncio.AbstractEventLoop):
    """Chạy event loop mãi mãi trong background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Lấy hoặc tạo event loop chạy trong background thread."""
    global _loop, _thread
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_start_background_loop, args=(_loop,), daemon=True)
        _thread.start()
    return _loop


def run_async(coro: Coroutine) -> Any:
    """
    Chạy một coroutine trên background event loop và chờ kết quả.

    Sử dụng asyncio.run_coroutine_threadsafe() để submit coroutine
    vào loop background và .result() để block cho đến khi hoàn thành.
    """
    loop = get_or_create_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


def shutdown_loop():
    """Dừng background event loop."""
    global _loop, _thread
    if _loop is not None and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)
        if _thread is not None:
            _thread.join(timeout=10)
        _loop.close()
        _loop = None
        _thread = None

"""
TikTok Scraping API - Flask REST API bọc TikTok-Api

Sử dụng Swagger UI (Flasgger) cho tài liệu API.
Truy cập: http://localhost:5000/apidocs

Yêu cầu:
    - Header x-cookie (bắt buộc): Cookie TikTok, server tự extract msToken
    - Header x-proxy (tuỳ chọn): Proxy URL
"""

import sys
import os
import logging
import atexit

# Thêm thư mục cha vào sys.path để import TikTokApi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, request, jsonify
from flasgger import Swagger

from async_helper import run_async, shutdown_loop
from tiktok_service import service
from routes import register_routes

# ============================================================
# Cấu hình logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("flask_app")

# ============================================================
# Khởi tạo Flask app
# ============================================================
app = Flask(__name__)

# ============================================================
# Cấu hình Swagger (Flasgger)
# ============================================================
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "TikTok Scraping API",
        "description": (
            "REST API để thu thập dữ liệu từ TikTok.\n\n"
            "**Hướng dẫn sử dụng:**\n"
            "1. Lấy cookie TikTok từ trình duyệt (bao gồm msToken)\n"
            "2. Truyền cookie vào header `x-cookie` (bắt buộc)\n"
            "3. Truyền proxy vào header `x-proxy` (tuỳ chọn)\n\n"
            "**Định dạng cookie:** `msToken=xxx; tt_webid=yyy; tt_csrf_token=zzz; ...`\n\n"
            "**Định dạng proxy:** `http://host:port` hoặc `http://user:pass@host:port`\n\n"
            "**Lưu ý:** Server sẽ tự trích xuất msToken từ cookie string. "
            "Mỗi request sẽ tạo 1 session Playwright mới với cookie/proxy riêng."
        ),
        "version": "1.0.0",
        "contact": {
            "name": "TikTok Scraping API",
        },
    },
    "basePath": "/",
    "schemes": ["https", "http"],
    "tags": [
        {
            "name": "Xu hướng (Trending)",
            "description": "Lấy video đang thịnh hành trên TikTok",
        },
        {
            "name": "Người dùng (User)",
            "description": "Lấy thông tin, video, liked, playlist của người dùng",
        },
        {
            "name": "Hashtag",
            "description": "Lấy thông tin hashtag và video theo hashtag",
        },
        {
            "name": "Video",
            "description": "Lấy thông tin, bình luận, video liên quan, và tải video",
        },
        {
            "name": "Âm thanh (Sound)",
            "description": "Lấy thông tin âm thanh và video sử dụng âm thanh đó",
        },
        {
            "name": "Tìm kiếm (Search)",
            "description": "Tìm kiếm người dùng và video trên TikTok",
        },
        {
            "name": "Playlist",
            "description": "Lấy thông tin playlist và video trong playlist",
        },
    ],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# ============================================================
# Middleware: Kiểm tra header x-cookie
# ============================================================
# Danh sách các route không cần cookie (Swagger UI, static, etc.)
EXEMPT_PREFIXES = ("/apidocs", "/apispec", "/flasgger_static", "/health", "/favicon")


@app.before_request
def check_cookie_header():
    """Kiểm tra header x-cookie trước mỗi request API."""
    if any(request.path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
        return None

    cookie = request.headers.get("x-cookie")
    if not cookie:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Thiếu header 'x-cookie'. Vui lòng cung cấp cookie TikTok."
        }), 401


# ============================================================
# Health check endpoint
# ============================================================
@app.route("/health", methods=["GET"])
def health_check():
    """
    Kiểm tra trạng thái server
    ---
    tags:
      - Hệ thống
    summary: Kiểm tra trạng thái server
    description: Trả về trạng thái hoạt động của server và browser Playwright.
    responses:
      200:
        description: Server đang hoạt động
    """
    return jsonify({
        "status": "ok",
        "browser_initialized": service._initialized,
        "active_sessions": len(service.api.sessions) if service.api else 0,
    })


# ============================================================
# Error handlers
# ============================================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "data": None,
        "message": "Endpoint không tồn tại"
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "success": False,
        "data": None,
        "message": "Phương thức HTTP không được hỗ trợ"
    }), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "success": False,
        "data": None,
        "message": f"Lỗi server nội bộ: {str(e)}"
    }), 500


# ============================================================
# Đăng ký routes
# ============================================================
register_routes(app)


# ============================================================
# Khởi tạo và dọn dẹp
# ============================================================
def init_browser():
    """Khởi tạo Playwright browser khi startup."""
    logger.info("Đang khởi tạo Playwright browser...")
    run_async(service.init_browser())
    logger.info("Playwright browser đã sẵn sàng!")


def cleanup():
    """Dọn dẹp tài nguyên khi tắt server."""
    logger.info("Đang dọn dẹp tài nguyên...")
    try:
        run_async(service.shutdown())
    except Exception as e:
        logger.error(f"Lỗi khi dọn dẹp: {e}")
    shutdown_loop()
    logger.info("Đã dọn dẹp xong!")


atexit.register(cleanup)


# ============================================================
# Main
# ============================================================
# Khởi tạo browser khi import (cho cả gunicorn lẫn chạy trực tiếp)
try:
    init_browser()
except Exception as e:
    logger.error(f"Không thể khởi tạo Playwright browser: {e}")
    logger.error("Server sẽ chạy nhưng các API scraping sẽ không hoạt động cho đến khi browser được khởi tạo lại.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("=" * 60)
    logger.info("TikTok Scraping API đang chạy!")
    logger.info(f"Swagger UI: http://localhost:{port}/apidocs/")
    logger.info(f"Health check: http://localhost:{port}/health")
    logger.info("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)

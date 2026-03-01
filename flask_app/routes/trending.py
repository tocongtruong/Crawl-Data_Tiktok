"""
Trending Routes - Endpoint lấy video xu hướng trên TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

trending_bp = Blueprint("trending", __name__)


@trending_bp.route("/api/trending/videos", methods=["GET"])
def trending_videos():
    """
    Lấy danh sách video xu hướng (trending)
    ---
    tags:
      - Xu hướng (Trending)
    summary: Lấy danh sách video xu hướng
    description: |
      Lấy danh sách video đang thịnh hành (trending) trên TikTok.
      Tương tự trang "Dành cho bạn" (For You) trên TikTok.
    parameters:
      - name: x-cookie
        in: header
        type: string
        required: true
        description: Cookie TikTok (bắt buộc). Server sẽ tự trích xuất msToken từ cookie này.
      - name: x-proxy
        in: header
        type: string
        required: false
        description: "Proxy (tuỳ chọn). Định dạng: http://host:port hoặc http://user:pass@host:port"
      - name: count
        in: query
        type: integer
        default: 30
        description: Số lượng video muốn lấy
    responses:
      200:
        description: Thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: array
              items:
                type: object
            message:
              type: string
              example: null
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    count = request.args.get("count", 30, type=int)

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            videos = []
            async for video in service.api.trending.videos(count=count, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

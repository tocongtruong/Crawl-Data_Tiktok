"""
Hashtag Routes - Endpoint lấy thông tin hashtag TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

hashtag_bp = Blueprint("hashtag", __name__)


@hashtag_bp.route("/api/hashtag/<name>/info", methods=["GET"])
def hashtag_info(name):
    """
    Lấy thông tin hashtag
    ---
    tags:
      - Hashtag
    summary: Lấy thông tin chi tiết của hashtag
    description: |
      Lấy thông tin chi tiết của một hashtag trên TikTok.
      Bao gồm: ID hashtag, tên, số lượt xem, v.v.
    parameters:
      - name: x-cookie
        in: header
        type: string
        required: true
        description: Cookie TikTok (bắt buộc).
      - name: x-proxy
        in: header
        type: string
        required: false
        description: "Proxy (tuỳ chọn)."
      - name: name
        in: path
        type: string
        required: true
        description: "Tên hashtag (vd: funny)"
    responses:
      200:
        description: Thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
            message:
              type: string
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            tag = service.api.hashtag(name=name)
            data = await tag.info(session_index=idx)
            return {
                "id": getattr(tag, "id", None),
                "name": getattr(tag, "name", None),
                "as_dict": getattr(tag, "as_dict", {}),
            }

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@hashtag_bp.route("/api/hashtag/<name>/videos", methods=["GET"])
def hashtag_videos(name):
    """
    Lấy danh sách video theo hashtag
    ---
    tags:
      - Hashtag
    summary: Lấy video theo hashtag
    description: |
      Lấy danh sách video được gắn hashtag cụ thể trên TikTok.
      Có thể phân trang qua tham số cursor.
    parameters:
      - name: x-cookie
        in: header
        type: string
        required: true
        description: Cookie TikTok (bắt buộc).
      - name: x-proxy
        in: header
        type: string
        required: false
        description: "Proxy (tuỳ chọn)."
      - name: name
        in: path
        type: string
        required: true
        description: "Tên hashtag (vd: funny)"
      - name: hashtag_id
        in: query
        type: string
        required: false
        description: ID của hashtag (tuỳ chọn, nếu có sẽ nhanh hơn)
      - name: count
        in: query
        type: integer
        default: 30
        description: Số lượng video muốn lấy
      - name: cursor
        in: query
        type: integer
        default: 0
        description: Vị trí bắt đầu
    responses:
      200:
        description: Thành công
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: array
              items:
                type: object
            message:
              type: string
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    count = request.args.get("count", 30, type=int)
    cursor = request.args.get("cursor", 0, type=int)
    hashtag_id = request.args.get("hashtag_id")

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            tag = service.api.hashtag(name=name, id=hashtag_id)
            videos = []
            async for video in tag.videos(count=count, cursor=cursor, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

"""
Sound Routes - Endpoint lấy thông tin âm thanh TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

sound_bp = Blueprint("sound", __name__)


@sound_bp.route("/api/sound/<sound_id>/info", methods=["GET"])
def sound_info(sound_id):
    """
    Lấy thông tin âm thanh
    ---
    tags:
      - Âm thanh (Sound)
    summary: Lấy thông tin chi tiết của âm thanh
    description: |
      Lấy thông tin chi tiết của một âm thanh (nhạc nền) trên TikTok.
      Bao gồm: tên bài hát, nghệ sĩ, thời lượng, v.v.
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
      - name: sound_id
        in: path
        type: string
        required: true
        description: ID của âm thanh TikTok
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
              properties:
                id:
                  type: string
                title:
                  type: string
                duration:
                  type: integer
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
            sound = service.api.sound(id=sound_id)
            await sound.info(session_index=idx)
            return {
                "id": getattr(sound, "id", None),
                "title": getattr(sound, "title", None),
                "duration": getattr(sound, "duration", None),
                "as_dict": getattr(sound, "as_dict", {}),
            }

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@sound_bp.route("/api/sound/<sound_id>/videos", methods=["GET"])
def sound_videos(sound_id):
    """
    Lấy danh sách video sử dụng âm thanh
    ---
    tags:
      - Âm thanh (Sound)
    summary: Lấy video sử dụng âm thanh
    description: |
      Lấy danh sách video TikTok sử dụng một âm thanh (nhạc nền) cụ thể.
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
      - name: sound_id
        in: path
        type: string
        required: true
        description: ID của âm thanh TikTok
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

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            sound = service.api.sound(id=sound_id)
            videos = []
            async for video in sound.videos(count=count, cursor=cursor, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

"""
Playlist Routes - Endpoint lấy thông tin playlist TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

playlist_bp = Blueprint("playlist", __name__)


@playlist_bp.route("/api/playlist/<playlist_id>/info", methods=["GET"])
def playlist_info(playlist_id):
    """
    Lấy thông tin playlist
    ---
    tags:
      - Playlist
    summary: Lấy thông tin chi tiết playlist
    description: |
      Lấy thông tin chi tiết của một playlist TikTok theo ID.
      Bao gồm: tên playlist, người tạo, số video, ảnh bìa, v.v.
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
      - name: playlist_id
        in: path
        type: string
        required: true
        description: ID của playlist TikTok
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
                name:
                  type: string
                video_count:
                  type: integer
                cover_url:
                  type: string
                creator:
                  type: string
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
            playlist = service.api.playlist(id=playlist_id)
            await playlist.info(session_index=idx)
            creator_username = None
            if hasattr(playlist, "creator") and playlist.creator:
                creator_username = getattr(playlist.creator, "username", None)
            return {
                "id": getattr(playlist, "id", None),
                "name": getattr(playlist, "name", None),
                "video_count": getattr(playlist, "video_count", None),
                "cover_url": getattr(playlist, "cover_url", None),
                "creator": creator_username,
                "as_dict": getattr(playlist, "as_dict", {}),
            }

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@playlist_bp.route("/api/playlist/<playlist_id>/videos", methods=["GET"])
def playlist_videos(playlist_id):
    """
    Lấy danh sách video trong playlist
    ---
    tags:
      - Playlist
    summary: Lấy video trong playlist
    description: |
      Lấy danh sách video thuộc một playlist TikTok cụ thể.
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
      - name: playlist_id
        in: path
        type: string
        required: true
        description: ID của playlist TikTok
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
            playlist = service.api.playlist(id=playlist_id)
            videos = []
            async for video in playlist.videos(count=count, cursor=cursor, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

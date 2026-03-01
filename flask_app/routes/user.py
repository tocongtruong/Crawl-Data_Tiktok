"""
User Routes - Endpoint lấy thông tin người dùng TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/user/<username>/info", methods=["GET"])
def user_info(username):
    """
    Lấy thông tin người dùng
    ---
    tags:
      - Người dùng (User)
    summary: Lấy thông tin chi tiết của người dùng
    description: |
      Lấy thông tin chi tiết của một người dùng TikTok theo username.
      Bao gồm: số follower, following, like, bio, avatar, v.v.
    parameters:
      - name: x-cookie
        in: header
        type: string
        required: true
        description: Cookie TikTok (bắt buộc). Server sẽ tự trích xuất msToken.
      - name: x-proxy
        in: header
        type: string
        required: false
        description: "Proxy (tuỳ chọn). Định dạng: http://host:port hoặc http://user:pass@host:port"
      - name: username
        in: path
        type: string
        required: true
        description: "Username của người dùng TikTok (vd: therock)"
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
            user = service.api.user(username=username)
            user_data = await user.info(session_index=idx)
            return user_data

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@user_bp.route("/api/user/<username>/videos", methods=["GET"])
def user_videos(username):
    """
    Lấy danh sách video của người dùng
    ---
    tags:
      - Người dùng (User)
    summary: Lấy danh sách video của người dùng
    description: |
      Lấy danh sách video đã đăng của một người dùng TikTok.
      Cần cung cấp sec_uid và user_id (qua query param) để phân trang chính xác,
      hoặc chỉ cần username (sẽ tự lấy info trước).
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
      - name: username
        in: path
        type: string
        required: true
        description: Username của người dùng TikTok
      - name: sec_uid
        in: query
        type: string
        required: false
        description: sec_uid của người dùng (tuỳ chọn, nếu có sẽ nhanh hơn)
      - name: user_id
        in: query
        type: string
        required: false
        description: user_id của người dùng (tuỳ chọn)
      - name: count
        in: query
        type: integer
        default: 30
        description: Số lượng video muốn lấy
      - name: cursor
        in: query
        type: integer
        default: 0
        description: Vị trí bắt đầu (dùng để phân trang)
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
    sec_uid = request.args.get("sec_uid")
    user_id = request.args.get("user_id")

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            user = service.api.user(username=username, sec_uid=sec_uid, user_id=user_id)
            if not sec_uid:
                await user.info(session_index=idx)
            videos = []
            async for video in user.videos(count=count, cursor=cursor, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@user_bp.route("/api/user/<username>/liked", methods=["GET"])
def user_liked(username):
    """
    Lấy danh sách video đã thích của người dùng
    ---
    tags:
      - Người dùng (User)
    summary: Lấy video đã thích của người dùng
    description: |
      Lấy danh sách video mà người dùng đã thích (like).
      Chỉ hoạt động nếu người dùng đã công khai danh sách liked.
      Cần cung cấp sec_uid để hoạt động chính xác.
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
      - name: username
        in: path
        type: string
        required: true
        description: Username của người dùng TikTok
      - name: sec_uid
        in: query
        type: string
        required: true
        description: sec_uid của người dùng (bắt buộc cho endpoint này)
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
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    count = request.args.get("count", 30, type=int)
    cursor = request.args.get("cursor", 0, type=int)
    sec_uid = request.args.get("sec_uid")

    if not sec_uid:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Tham số sec_uid là bắt buộc cho endpoint này"
        }), 400

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            user = service.api.user(username=username, sec_uid=sec_uid)
            videos = []
            async for video in user.liked(count=count, cursor=cursor, session_index=idx):
                videos.append(video.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@user_bp.route("/api/user/<username>/playlists", methods=["GET"])
def user_playlists(username):
    """
    Lấy danh sách playlist của người dùng
    ---
    tags:
      - Người dùng (User)
    summary: Lấy playlist của người dùng
    description: Lấy danh sách playlist mà người dùng TikTok đã tạo.
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
      - name: username
        in: path
        type: string
        required: true
        description: Username của người dùng TikTok
      - name: count
        in: query
        type: integer
        default: 20
        description: Số lượng playlist muốn lấy
      - name: cursor
        in: query
        type: integer
        default: 0
        description: Vị trí bắt đầu
    responses:
      200:
        description: Thành công
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    count = request.args.get("count", 20, type=int)
    cursor = request.args.get("cursor", 0, type=int)

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            user = service.api.user(username=username)
            playlists = []
            async for playlist in user.playlists(count=count, cursor=cursor, session_index=idx):
                playlists.append({
                    "id": getattr(playlist, "id", None),
                    "name": getattr(playlist, "name", None),
                    "video_count": getattr(playlist, "video_count", None),
                    "cover_url": getattr(playlist, "cover_url", None),
                    "as_dict": getattr(playlist, "as_dict", {}),
                })
            return playlists

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

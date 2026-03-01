"""
Video Routes - Endpoint lấy thông tin video TikTok.
"""

from flask import Blueprint, request, jsonify, Response
from async_helper import run_async
from tiktok_service import service

video_bp = Blueprint("video", __name__)


@video_bp.route("/api/video/info", methods=["GET"])
def video_info():
    """
    Lấy thông tin video
    ---
    tags:
      - Video
    summary: Lấy thông tin chi tiết của video
    description: |
      Lấy thông tin chi tiết của một video TikTok theo URL đầy đủ.
      Bao gồm: mô tả, tác giả, số like/comment/share, nhạc nền, hashtag, v.v.

      **Lưu ý:** Endpoint này dùng HTTP request nên sẽ chậm hơn, tránh gọi quá nhiều.
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
      - name: url
        in: query
        type: string
        required: true
        description: "URL đầy đủ của video TikTok (vd: https://www.tiktok.com/@user/video/1234567890)"
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
      400:
        description: Thiếu tham số url
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    video_url = request.args.get("url")

    if not video_url:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Tham số 'url' là bắt buộc"
        }), 400

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            video = service.api.video(url=video_url, session_index=idx)
            data = await video.info(session_index=idx)
            return data

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@video_bp.route("/api/video/<video_id>/comments", methods=["GET"])
def video_comments(video_id):
    """
    Lấy bình luận của video
    ---
    tags:
      - Video
    summary: Lấy danh sách bình luận của video
    description: |
      Lấy danh sách bình luận (comment) của một video TikTok theo video ID.
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
      - name: video_id
        in: path
        type: string
        required: true
        description: ID của video TikTok
      - name: count
        in: query
        type: integer
        default: 20
        description: Số lượng bình luận muốn lấy
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
                properties:
                  id:
                    type: string
                  text:
                    type: string
                  author:
                    type: string
                  likes_count:
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
    count = request.args.get("count", 20, type=int)
    cursor = request.args.get("cursor", 0, type=int)

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            video = service.api.video(id=video_id)
            comments = []
            async for comment in video.comments(count=count, cursor=cursor, session_index=idx):
                comments.append({
                    "id": getattr(comment, "id", None),
                    "text": getattr(comment, "text", None),
                    "author": str(getattr(comment, "author", None)),
                    "likes_count": getattr(comment, "likes_count", 0),
                    "as_dict": getattr(comment, "as_dict", {}),
                })
            return comments

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@video_bp.route("/api/video/<video_id>/related", methods=["GET"])
def video_related(video_id):
    """
    Lấy video liên quan
    ---
    tags:
      - Video
    summary: Lấy danh sách video liên quan
    description: |
      Lấy danh sách video liên quan đến một video TikTok cụ thể.
      TikTok sẽ gợi ý các video tương tự dựa trên nội dung.
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
      - name: video_id
        in: path
        type: string
        required: true
        description: ID của video TikTok
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

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            video = service.api.video(id=video_id)
            videos = []
            async for v in video.related_videos(count=count, cursor=cursor, session_index=idx):
                videos.append(v.as_dict)
            return videos

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@video_bp.route("/api/video/download", methods=["GET"])
def video_download():
    """
    Tải video TikTok
    ---
    tags:
      - Video
    summary: Tải video TikTok (trả về file MP4)
    description: |
      Tải video TikTok theo URL đầy đủ. Trả về dữ liệu video dạng binary (MP4).

      **Quy trình:** Server sẽ gọi video.info() trước để lấy downloadAddr,
      sau đó tải video qua video.bytes().

      **Lưu ý:** Endpoint này có thể mất thời gian do phải tải toàn bộ video.
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
      - name: url
        in: query
        type: string
        required: true
        description: URL đầy đủ của video TikTok
    responses:
      200:
        description: File video MP4 (binary)
        schema:
          type: file
      400:
        description: Thiếu tham số url
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    produces:
      - video/mp4
      - application/json
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    video_url = request.args.get("url")

    if not video_url:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Tham số 'url' là bắt buộc"
        }), 400

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            video = service.api.video(url=video_url, session_index=idx)
            await video.info(session_index=idx)
            video_bytes = await video.bytes(session_index=idx)
            return video_bytes

    try:
        data = run_async(_fetch())
        return Response(
            data,
            mimetype="video/mp4",
            headers={
                "Content-Disposition": "attachment; filename=video.mp4",
                "Content-Type": "video/mp4",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

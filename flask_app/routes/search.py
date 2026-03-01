"""
Search Routes - Endpoint tìm kiếm trên TikTok.
"""

from flask import Blueprint, request, jsonify
from async_helper import run_async
from tiktok_service import service

search_bp = Blueprint("search", __name__)


@search_bp.route("/api/search/users", methods=["GET"])
def search_users():
    """
    Tìm kiếm người dùng
    ---
    tags:
      - Tìm kiếm (Search)
    summary: Tìm kiếm người dùng TikTok
    description: |
      Tìm kiếm người dùng TikTok theo từ khoá.

      **Lưu ý:** msToken cần phải được lấy từ trình duyệt đã thực hiện tìm kiếm trước đó
      thì endpoint này mới hoạt động.
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
      - name: keyword
        in: query
        type: string
        required: true
        description: Từ khoá tìm kiếm
      - name: count
        in: query
        type: integer
        default: 10
        description: Số lượng kết quả muốn lấy
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
      400:
        description: Thiếu từ khoá
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    keyword = request.args.get("keyword")
    count = request.args.get("count", 10, type=int)
    cursor = request.args.get("cursor", 0, type=int)

    if not keyword:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Tham số 'keyword' là bắt buộc"
        }), 400

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            users = []
            async for user in service.api.search.users(keyword, count=count, cursor=cursor, session_index=idx):
                users.append({
                    "user_id": getattr(user, "user_id", None),
                    "username": getattr(user, "username", None),
                    "sec_uid": getattr(user, "sec_uid", None),
                    "as_dict": getattr(user, "as_dict", {}),
                })
            return users

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500


@search_bp.route("/api/search/videos", methods=["GET"])
def search_videos():
    """
    Tìm kiếm video
    ---
    tags:
      - Tìm kiếm (Search)
    summary: Tìm kiếm video TikTok theo từ khoá
    description: |
      Tìm kiếm video TikTok theo từ khoá. Sử dụng API search trực tiếp
      (tương tự video_keyword_search_example.py).

      Hỗ trợ phân trang thông qua tham số cursor.
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
      - name: keyword
        in: query
        type: string
        required: true
        description: "Từ khoá tìm kiếm (vd: funny cats)"
      - name: count
        in: query
        type: integer
        default: 10
        description: Số lượng video muốn lấy (mặc định 10, mỗi trang tối đa 10)
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
              type: object
              properties:
                videos:
                  type: array
                  items:
                    type: object
                has_more:
                  type: boolean
                cursor:
                  type: integer
            message:
              type: string
      400:
        description: Thiếu từ khoá
      401:
        description: Thiếu cookie
      500:
        description: Lỗi server
    """
    cookie_str = request.headers.get("x-cookie")
    proxy_str = request.headers.get("x-proxy")
    keyword = request.args.get("keyword")
    count = request.args.get("count", 10, type=int)
    cursor = request.args.get("cursor", 0, type=int)

    if not keyword:
        return jsonify({
            "success": False,
            "data": None,
            "message": "Tham số 'keyword' là bắt buộc"
        }), 400

    async def _fetch():
        async with service.session_context(cookie_str, proxy_str) as (session, idx):
            search_url = "https://www.tiktok.com/api/search/item/full/"
            all_videos = []
            current_cursor = cursor
            remaining = count
            has_more = False

            while remaining > 0:
                params = {
                    "keyword": keyword,
                    "count": min(10, remaining),
                    "cursor": current_cursor,
                    "source": "search_video",
                }

                response = await service.api.make_request(
                    url=search_url, params=params, session_index=idx
                )

                items = response.get("item_list", [])
                for item in items:
                    all_videos.append(item)
                    remaining -= 1
                    if remaining <= 0:
                        break

                has_more = response.get("has_more", False)
                current_cursor = response.get("cursor", 0)

                if not has_more or not items:
                    break

            return {
                "videos": all_videos,
                "has_more": has_more,
                "cursor": current_cursor,
            }

    try:
        data = run_async(_fetch())
        return jsonify({"success": True, "data": data, "message": None})
    except Exception as e:
        return jsonify({"success": False, "data": None, "message": str(e)}), 500

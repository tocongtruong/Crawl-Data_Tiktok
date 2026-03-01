"""
Routes package - Đăng ký tất cả blueprint vào Flask app.
"""

from routes.trending import trending_bp
from routes.user import user_bp
from routes.hashtag import hashtag_bp
from routes.video import video_bp
from routes.sound import sound_bp
from routes.search import search_bp
from routes.playlist import playlist_bp


def register_routes(app):
    """Đăng ký tất cả blueprint routes vào Flask app."""
    app.register_blueprint(trending_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(hashtag_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(sound_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(playlist_bp)

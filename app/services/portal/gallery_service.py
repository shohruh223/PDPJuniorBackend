from __future__ import annotations

from app.models.gallery import GalleryPost
from app.serializers.media import build_file_url


def _map_media_item(item: dict, request=None) -> dict:
    data = dict(item or {})
    src = data.get("src") or data.get("url") or ""
    if src:
        resolved = build_file_url(src, request)
        data["src"] = resolved
        if "url" in data:
            data["url"] = resolved
    return data


def serialize_gallery_post(post: GalleryPost, request=None) -> dict:
    media = post.media or []
    if not media and post.cover_image:
        media = [{
            "type": "image",
            "src": post.cover_image,
            "contain": post.cover_contain,
            "bg": post.cover_bg,
        }]

    media = [_map_media_item(item, request) for item in media if isinstance(item, dict)]
    image = build_file_url(post.cover_image, request) or (
        media[0].get("src") if media else ""
    )

    return {
        "id": str(post.id),
        "category": post.category or {},
        "icon": post.icon or "📰",
        "date": post.date,
        "views": post.views,
        "views_count": post.views_count,
        "image": image,
        "contain": post.cover_contain,
        "bg": post.cover_bg,
        "title": post.title or {},
        "description": post.description or {},
        "media": media,
    }


def get_gallery_posts(request=None):
    posts = GalleryPost.objects.filter(is_active=True).order_by("sort_order", "-created_at")
    return [serialize_gallery_post(post, request) for post in posts]

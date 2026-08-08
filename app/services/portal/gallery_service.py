from __future__ import annotations

from app.models.gallery import GalleryPost


def serialize_gallery_post(post: GalleryPost, request=None) -> dict:
    media = post.media or []
    if not media and post.cover_image:
        media = [{
            "type": "image",
            "src": post.cover_image,
            "contain": post.cover_contain,
            "bg": post.cover_bg,
        }]

    image = post.cover_image or (media[0].get("src") if media else "")

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

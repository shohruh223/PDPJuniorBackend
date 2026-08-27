from django.core.files.storage import default_storage
from django.conf import settings


def build_file_url(path, request=None):
    """Relative / static / http pathlardan ochiladigan URL yasaydi.

    USE_R2=1 bo'lsa static/ yo'llar ham R2 public URL ga aylantiriladi
    (migratsiya qilingan assetlar uchun).
    """
    if not path:
        return None

    if isinstance(path, str) and (
        path.startswith("http://") or path.startswith("https://")
    ):
        return path

    path = str(path).lstrip("/")

    if isinstance(path, str) and path.startswith("static/"):
        if getattr(settings, "USE_R2", False):
            url = default_storage.url(path)
            if request and not url.startswith(("http://", "https://")):
                return request.build_absolute_uri(url)
            return url
        # R2 yo'q: frontend o'z originidan o'qiydi
        return path

    url = default_storage.url(path)

    if request and not url.startswith("http://") and not url.startswith("https://"):
        return request.build_absolute_uri(url)

    return url

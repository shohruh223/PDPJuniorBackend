from django.core.files.storage import default_storage


def build_file_url(path, request=None):
    if not path:
        return None

    if isinstance(path, str) and (
        path.startswith("http://") or path.startswith("https://")
    ):
        return path
    if isinstance(path, str) and path.startswith("static/"):
        # Frontend ZIP ichidagi asset yo'li: klient o'z originidan yuklaydi.
        return path

    url = default_storage.url(path)

    if request and not url.startswith("http://") and not url.startswith("https://"):
        return request.build_absolute_uri(url)

    return url
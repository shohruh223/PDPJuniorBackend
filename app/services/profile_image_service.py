from app.serializers.media import build_file_url


def build_profile_image_url(user, request=None):
    if user.photo:
        url = user.photo.url
        if request and not str(url).startswith(("http://", "https://")):
            return request.build_absolute_uri(url)
        return url

    profile = getattr(user, "student_profile", None)
    if profile and profile.avatar_url:
        return build_file_url(profile.avatar_url, request)

    return None

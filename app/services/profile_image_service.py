def build_profile_image_url(user, request=None):
    if user.photo:
        if request:
            return request.build_absolute_uri(user.photo.url)
        return user.photo.url

    profile = getattr(user, "student_profile", None)
    if profile and profile.avatar_url:
        return profile.avatar_url

    return None

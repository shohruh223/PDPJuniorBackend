from django.core.cache import cache

UNLOCKED_MODULES_CACHE_TTL = 60 * 60  # 1 soat
COMPLETED_LESSONS_CACHE_TTL = 60 * 60  # 1 soat


def unlocked_modules_cache_key(user_id, course_id):
    return f"unlocked_modules:{user_id}:{course_id}"


def completed_lessons_cache_key(user_id, course_id):
    return f"completed_lessons:{user_id}:{course_id}"


def invalidate_unlocked_modules_cache(user, course=None, *, course_id=None):
    """Test yakunlanganda progress cache ni yangilash uchun."""
    if course_id is None and course is not None:
        course_id = course.id
    if course_id is None and hasattr(user, "student_profile"):
        profile_course = getattr(user.student_profile, "course", None)
        if profile_course:
            course_id = profile_course.id
    if course_id:
        cache.delete(unlocked_modules_cache_key(user.id, course_id))
        cache.delete(completed_lessons_cache_key(user.id, course_id))


def invalidate_user_progress_cache(user, *, course_id=None):
    invalidate_unlocked_modules_cache(user, course_id=course_id)

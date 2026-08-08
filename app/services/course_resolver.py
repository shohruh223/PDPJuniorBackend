from app.models.question import Course


GROUP_PREFIX_TO_COURSE = {
    "P": "Python",
    "F": "Frontend",
    "M": "Microbots",
}


def resolve_course_name_from_group(group_name: str | None) -> str | None:
    if not group_name:
        return None

    group_name = group_name.strip()
    if not group_name:
        return None

    prefix = group_name[0].upper()
    return GROUP_PREFIX_TO_COURSE.get(prefix)


def get_or_create_course_from_group(group_name: str):
    course_name = resolve_course_name_from_group(group_name)
    if not course_name:
        return None

    course, _ = Course.objects.get_or_create(name=course_name)
    return course
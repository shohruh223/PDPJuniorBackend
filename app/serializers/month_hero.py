from rest_framework import serializers

from app.models.month_hero import MonthHero
from app.services.profile_image_service import build_profile_image_url


MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


class MonthHeroSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    name = serializers.SerializerMethodField()

    course_id = serializers.IntegerField(source="student_profile.course_id", read_only=True)
    course = serializers.SerializerMethodField()

    branch_id = serializers.IntegerField(source="student_profile.branch_id", read_only=True)
    branch = serializers.SerializerMethodField()

    score = serializers.SerializerMethodField()

    period = serializers.DateField(read_only=True)
    year = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    month_name = serializers.SerializerMethodField()

    avatar = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = MonthHero
        fields = [
            "id",
            "name",

            "course_id",
            "course",

            "branch_id",
            "branch",

            "score",

            "period",
            "year",
            "month",
            "month_name",

            "avatar",
            "rank",
        ]

    def get_name(self, obj):
        return obj.student_profile.user.full_name

    def get_course(self, obj):
        course = obj.student_profile.course

        if not course:
            return None

        return {
            "id": course.id,
            "name": course.name,
        }

    def get_branch(self, obj):
        branch = obj.student_profile.branch

        if not branch:
            return None

        return {
            "id": branch.id,
            "name": branch.name,
        }

    def get_score(self, obj):
        return obj.student_profile.total_score

    def get_year(self, obj):
        if not obj.period:
            return None
        return obj.period.year

    def get_month(self, obj):
        if not obj.period:
            return None
        return obj.period.month

    def get_month_name(self, obj):
        if not obj.period:
            return None
        return MONTH_NAMES.get(obj.period.month)

    def get_avatar(self, obj):
        return build_profile_image_url(
            obj.student_profile.user,
            request=self.context.get("request"),
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks", {})
        return ranks.get(obj.id)
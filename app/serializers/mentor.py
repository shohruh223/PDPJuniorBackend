from rest_framework import serializers
from app.models import Mentor
from app.serializers.media import build_file_url


class MentorSerializer(serializers.ModelSerializer):
    branch = serializers.IntegerField(source="branch_id", read_only=True)
    studentsCount = serializers.CharField(source="students_count", read_only=True)
    workingPeriodStart = serializers.DateField(
        source="working_period_start",
        read_only=True,
    )
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Mentor
        fields = (
            "id",
            "name",
            "role",
            "bio",
            "branch",
            "exp",
            "studentsCount",
            "workingPeriodStart",
            "avatar",
        )
        read_only_fields = fields

    def get_avatar(self, obj):
        request = self.context.get("request")
        data = obj.avatar or {}

        if isinstance(data, dict):
            path = data.get("url")
        else:
            path = None

        return build_file_url(path, request)
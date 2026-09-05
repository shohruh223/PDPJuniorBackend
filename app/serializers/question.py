from rest_framework import serializers

from app.utils.text import estimated_test_minutes
from app.models.question import Course, Lesson, Question, validate_i18n_json, Module



class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "name"]


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ("id", "course", "name", "order")


class LessonSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    questions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "course",
            "module",
            "name",
            "order",
            "questions_count",
        )

    def get_questions_count(self, obj):
        return obj.questions.count()


class QuestionBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "lesson",
            "text",
            "images",
            "options",
            "correct_option",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_text(self, value):
        try:
            validate_i18n_json(value)
        except Exception as e:
            raise serializers.ValidationError(getattr(e, "messages", [str(e)]))
        return value

    def validate_images(self, value):
        if value in (None, ""):
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError("images dict bo‘lishi kerak.")

        for key, image in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError("images kalitlari string bo‘lishi kerak.")
            if not isinstance(image, str):
                raise serializers.ValidationError(f"images['{key}'] string bo‘lishi kerak.")

        return value

    def validate_options(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("options dict bo‘lishi kerak.")

        option_count = len(value)
        if option_count < 2:
            raise serializers.ValidationError("Minimum 2 ta variant bo‘lishi kerak.")
        if option_count > 4:
            raise serializers.ValidationError("Maksimum 4 ta variant bo‘lishi mumkin.")

        allowed_keys = {"A", "B", "C", "D"}
        option_keys = set(value.keys())

        if not option_keys.issubset(allowed_keys):
            raise serializers.ValidationError("Variantlar faqat A, B, C, D bo‘lishi mumkin.")

        for key, item in value.items():
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"{key} qiymati dict bo‘lishi kerak.")

            try:
                validate_i18n_json(item)
            except Exception as e:
                messages = getattr(e, "messages", [str(e)])
                raise serializers.ValidationError({key: messages})

        return value

    def validate(self, attrs):
        options = attrs.get("options", getattr(self.instance, "options", None))
        correct_option = attrs.get("correct_option", getattr(self.instance, "correct_option", None))

        if isinstance(options, dict) and correct_option not in options:
            raise serializers.ValidationError({
                "correct_option": "correct_option options ichida mavjud bo‘lishi kerak."
            })

        return attrs


class QuestionWriteSerializer(QuestionBaseSerializer):
    lesson = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all())

    class Meta(QuestionBaseSerializer.Meta):
        fields = QuestionBaseSerializer.Meta.fields


class QuestionAdminReadSerializer(serializers.ModelSerializer):
    lesson = LessonSerializer(read_only=True)
    course = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "course",
            "lesson",
            "text",
            "images",
            "options",
            "correct_option",
            "created_at",
        ]

    def get_course(self, obj):
        if obj.lesson_id and obj.lesson.course_id:
            return CourseSerializer(obj.lesson.course).data
        return None


class StudentQuestionSerializer(serializers.ModelSerializer):
    """
    Student test ishlayotgan paytda correct_option ko‘rinmaydi.
    """
    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "images",
            "options",
        ]


class StudentQuestionResultSerializer(serializers.ModelSerializer):
    """
    Test tugagandan keyin correct_option ham ko‘rinadi.
    """
    selected_option = serializers.SerializerMethodField()
    is_correct = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "images",
            "options",
            "correct_option",
            "selected_option",
            "is_correct",
        ]

    def get_selected_option(self, obj):
        answers_map = self.context.get("answers_map", {})
        answer = answers_map.get(obj.id)
        return answer.selected_option if answer else None

    def get_is_correct(self, obj):
        answers_map = self.context.get("answers_map", {})
        answer = answers_map.get(obj.id)
        return answer.is_correct if answer else False


class StudentCourseLessonsSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(read_only=True)
    estimated_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "name",
            "questions_count",
            "estimated_duration_minutes",
        ]

    def get_estimated_duration_minutes(self, obj):
        return estimated_test_minutes(getattr(obj, "questions_count", 0))
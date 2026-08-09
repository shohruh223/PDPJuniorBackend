from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
import random
from app.models.question import Lesson, Question, Module
from app.models.test import TestSession, TestSessionQuestion, TestSessionAnswer
from app.serializers.question import CourseSerializer, LessonSerializer
from app.services.student.test_progress_service import is_module_unlocked


def pick_lang_value(data, lang="uz"):
    if isinstance(data, dict):
        return data.get(lang) or data.get("uz") or next(iter(data.values()), "")
    return data


class AllQuestionPublicSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "text", "image_url", "options"]

    def get_lang(self):
        return self.context.get("language") or "uz"

    def get_text(self, obj):
        return pick_lang_value(obj.text, self.get_lang())

    def get_options(self, obj):
        lang = self.get_lang()
        result = {}
        for key, value in (obj.options or {}).items():
            result[key] = pick_lang_value(value, lang)
        return result

    def get_image_url(self, obj):
        images = obj.images or {}
        if not isinstance(images, dict):
            return None

        lang = self.get_lang()
        return images.get(lang) or images.get("uz") or next(iter(images.values()), None)


class SessionQuestionSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()

    class Meta:
        model = TestSessionQuestion
        fields = ["id", "order", "question"]

    def get_question(self, obj):
        return AllQuestionPublicSerializer(
            obj.question,
            context=self.context,
        ).data


class TestSessionSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(read_only=True)
    lesson = LessonSerializer(read_only=True)
    course = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    remaining_seconds = serializers.IntegerField(read_only=True)
    answered_count = serializers.SerializerMethodField()

    class Meta:
        model = TestSession
        fields = [
            "session_id",
            "lesson",
            "module",
            "course",
            "total_questions",
            "duration_minutes",
            "started_at",
            "expires_at",
            "finished_at",
            "remaining_seconds",
            "answered_count",
            "is_finished",
        ]

    def get_course(self, obj):
        if obj.lesson_id and obj.lesson.course_id:
            return CourseSerializer(obj.lesson.course).data
        return None

    def get_module(self, obj):
        if obj.lesson_id and obj.lesson.module_id:
            return {
                "id": obj.lesson.module.id,
                "name": obj.lesson.module.name,
                "order": obj.lesson.module.order,
            }
        return None

    def get_answered_count(self, obj):
        return obj.answers.count()


class StudentLessonItemSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(read_only=True)
    estimated_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "name",
            "order",
            "questions_count",
            "estimated_duration_minutes",
        )

    def get_estimated_duration_minutes(self, obj):
        count = getattr(obj, "questions_count", 0) or 0
        return count + 1 if count > 0 else 1


class StudentModuleWithLessonsSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ("id", "name", "order", "lessons_count", "lessons")

    def get_lessons(self, obj):
        lessons = getattr(obj, "prefetched_lessons", None)
        if lessons is None:
            lessons = obj.lessons.all().order_by("order", "id")
        return StudentLessonItemSerializer(lessons, many=True).data

    def get_lessons_count(self, obj):
        lessons = getattr(obj, "prefetched_lessons", None)
        if lessons is not None:
            return len(lessons)
        return obj.lessons.count()


class StartTestSessionSerializer(serializers.Serializer):
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(),
        required=False,
        allow_null=True,
        source="module",
        help_text="Ixtiyoriy. Lesson tegishli bo‘lgan modul ID si",
    )
    lesson_id = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.select_related("course", "module").all(),
        source="lesson",
        help_text="Test boshlanadigan lesson ID si",
    )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        lesson = attrs["lesson"]
        module = attrs.get("module")

        if not user.is_authenticated:
            raise serializers.ValidationError("Autentifikatsiya talab qilinadi.")

        if getattr(user, "role", None) != "student":
            raise serializers.ValidationError("Faqat student test boshlashi mumkin.")

        student_course = None

        if hasattr(user, "student_profile"):
            profile = user.student_profile

            if profile.course:
                student_course = profile.course
            else:
                group_course_name = profile.resolve_course_name_from_group()
                if group_course_name:
                    student_course = lesson.course.__class__.objects.filter(
                        name__iexact=group_course_name
                    ).first()

        if not student_course:
            raise serializers.ValidationError({
                "lesson_id": "Student uchun course aniqlanmadi."
            })

        if lesson.course_id != student_course.id:
            raise serializers.ValidationError({
                "lesson_id": "Bu lesson studentning course'iga tegishli emas."
            })

        if not is_module_unlocked(user, student_course, lesson.module_id):
            raise serializers.ValidationError({
                "module_id": (
                    "Bu modul hali yopiq. Avval oldingi modul testlarini "
                    "to‘liq yakunlang."
                )
            })

        if module and lesson.module_id != module.id:
            raise serializers.ValidationError({
                "module_id": "Tanlangan module ushbu lessonga tegishli emas."
            })

        question_ids = list(
            Question.objects
            .filter(lesson=lesson)
            .values_list("id", flat=True)
        )

        questions_count = len(question_ids)

        if questions_count == 0:
            raise serializers.ValidationError({
                "lesson_id": "Bu lesson uchun savollar topilmadi."
            })

        random.shuffle(question_ids)

        questions_map = Question.objects.in_bulk(question_ids)
        questions = [
            questions_map[question_id]
            for question_id in question_ids
            if question_id in questions_map
        ]

        existing_session = TestSession.objects.filter(
            student=user,
            lesson=lesson,
            is_finished=False,
        ).first()

        if existing_session:
            if existing_session.is_expired():
                existing_session.finish()
            else:
                raise serializers.ValidationError({
                    "session": "Bu lesson bo‘yicha tugallanmagan test session mavjud."
                })

        attrs["questions"] = questions
        attrs["questions_count"] = questions_count
        attrs["duration_minutes"] = questions_count + 1

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        lesson = validated_data["lesson"]
        questions = validated_data["questions"]
        questions_count = validated_data["questions_count"]
        duration_minutes = validated_data["duration_minutes"]

        now = timezone.now()

        session = TestSession.objects.create(
            student=user,
            lesson=lesson,
            total_questions=questions_count,
            duration_minutes=duration_minutes,
            expires_at=now + timezone.timedelta(minutes=duration_minutes),
            is_finished=False,
        )

        TestSessionQuestion.objects.bulk_create([
            TestSessionQuestion(
                session=session,
                question=question,
                order=index,
            )
            for index, question in enumerate(questions, start=1)
        ])

        return session


class StartTestSessionResponseSerializer(serializers.Serializer):
    session = TestSessionSerializer()
    questions = SessionQuestionSerializer(many=True)


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(help_text="Javob yuborilayotgan savol ID si")
    selected_option = serializers.ChoiceField(
        choices=[choice[0] for choice in Question.OPTION_CHOICES],
        help_text="Tanlangan variant. Masalan: A, B, C yoki D",
    )

    def validate(self, attrs):
        session = self.context["session"]
        question_id = attrs["question_id"]

        if session.is_finished:
            raise serializers.ValidationError("Test allaqachon tugagan.")

        if session.is_expired():
            session.finish()
            raise serializers.ValidationError("Test vaqti tugagan.")

        session_item = TestSessionQuestion.objects.select_related("question").filter(
            session=session,
            question_id=question_id,
        ).first()

        if not session_item:
            raise serializers.ValidationError({
                "question_id": "Bu savol ushbu test sessionga tegishli emas."
            })

        attrs["session_item"] = session_item
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        session = self.context["session"]
        session_item = validated_data["session_item"]
        question = session_item.question
        selected_option = validated_data["selected_option"]
        new_is_correct = question.is_correct(selected_option)

        answer_obj = (
            TestSessionAnswer.objects
            .select_for_update()
            .filter(session=session, question=question)
            .first()
        )
        previous_is_correct = answer_obj.is_correct if answer_obj else False

        if answer_obj:
            answer_obj.selected_option = selected_option
            answer_obj.is_correct = new_is_correct
            answer_obj.save(update_fields=["selected_option", "is_correct"])
        else:
            answer_obj = TestSessionAnswer.objects.create(
                session=session,
                question=question,
                selected_option=selected_option,
                is_correct=new_is_correct,
            )

        if previous_is_correct != new_is_correct:
            from app.models.auth import StudentProfile

            student_profile = StudentProfile.objects.select_for_update().get(
                user=session.student
            )

            reward_delta = 1 if new_is_correct else -1

            student_profile.local_test_score = max(
                0,
                student_profile.local_test_score + reward_delta,
            )
            student_profile.test_coin = max(
                0,
                student_profile.test_coin + reward_delta,
            )
            student_profile.lesson_last_coin = max(
                0,
                (student_profile.lesson_last_coin or 0) + reward_delta
            )
            student_profile.recalculate_all_totals(save=False)
            student_profile.save(
                update_fields=[
                    "local_test_score",
                    "test_coin",
                    "lesson_last_coin",
                    "total_score",
                    "total_coin",
                    "updated_at",
                ]
            )

        return answer_obj


class SubmitAnswerResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(read_only=True)
    selected_option = serializers.CharField(read_only=True)
    is_correct = serializers.BooleanField(read_only=True)
    correct_option = serializers.CharField(read_only=True)
    show_correct_answer = serializers.BooleanField(read_only=True)
    finished = serializers.BooleanField(read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True, allow_null=True)


class ResultQuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    text = serializers.CharField()
    image_url = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    options = serializers.DictField(child=serializers.CharField(), default=dict)
    correct_option = serializers.CharField()
    selected_option = serializers.CharField(allow_null=True, required=False)
    is_correct = serializers.BooleanField()
    is_answered = serializers.BooleanField()


class TestSessionResultSerializer(serializers.Serializer):
    percent = serializers.IntegerField(min_value=0, max_value=100)
    spent_time = serializers.CharField()
    total = serializers.IntegerField(min_value=0)
    correct = serializers.IntegerField(min_value=0)
    wrong = serializers.IntegerField(min_value=0)
    unanswered = serializers.IntegerField(min_value=0)
    questions = ResultQuestionSerializer(many=True)
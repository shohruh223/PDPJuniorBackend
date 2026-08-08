from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.models.question import Lesson, Question
from app.permissions import IsStudentUserRole
from app.serializers.test import pick_lang_value


def question_to_frontend(question: Question, lang: str = "uz") -> dict:
    option_keys = sorted((question.options or {}).keys())
    answers = [
        pick_lang_value((question.options or {}).get(key), lang)
        for key in option_keys
    ]
    correct_index = 0
    if question.correct_option in option_keys:
        correct_index = option_keys.index(question.correct_option)

    return {
        "id": question.id,
        "text": pick_lang_value(question.text, lang),
        "answers": answers,
        "options": answers,
        "correct_index": correct_index,
        "correctIndex": correct_index,
    }


class LessonQuestionsAPIView(APIView):
    """
    Frontend lessons-data.js uchun: GET /api/student/lessons/{lesson_id}/questions
    """

    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Dars savollari"],
        operation_summary="Dars savollarini frontend formatida olish",
        operation_description=(
            "Berilgan `lesson_id` bo‘yicha barcha savollarni eski frontend "
            "`lessons-data.js` kutadigan formatda qaytaradi. Login qiling, URL pathga "
            "dars ID sini qo‘ying va ixtiyoriy `lang=uz|ru|en` yuboring. Har bir savolda "
            "`answers` va `options` bir xil tarjima qilingan variantlar ro‘yxati; "
            "`correct_index` va `correctIndex` esa bir xil, noldan boshlanuvchi to‘g‘ri "
            "javob indeksidir. Noma’lum til yuborilsa `uz` ishlatiladi."
        ),
        manual_parameters=[
            openapi.Parameter(
                "lesson_id",
                openapi.IN_PATH,
                description="Savollari olinadigan darsning butun sonli ID si.",
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
            openapi.Parameter(
                "lang",
                openapi.IN_QUERY,
                description="Savol va javoblar tili. Yuborilmasa yoki noto‘g‘ri bo‘lsa `uz`.",
                type=openapi.TYPE_STRING,
                enum=["uz", "ru", "en"],
                default="uz",
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="Dars savollari frontend formati bilan olindi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Savollar olindi.",
                    "data": {
                        "lesson_id": 101,
                        "questions": [{
                            "id": 501,
                            "text": "Python ro‘yxati qanday yaratiladi?",
                            "answers": ["[]", "{}", "()"],
                            "options": ["[]", "{}", "()"],
                            "correct_index": 0,
                            "correctIndex": 0,
                        }],
                    },
                }},
            ),
            401: openapi.Response(description="Access token yuborilmagan yoki yaroqsiz."),
            403: openapi.Response(description="Foydalanuvchida student roli yo‘q."),
            404: openapi.Response(
                description="lesson_id bo‘yicha dars topilmadi.",
                examples={"application/json": {
                    "success": False,
                    "message": "Dars topilmadi.",
                }},
            ),
        },
    )
    def get(self, request, lesson_id, *args, **kwargs):
        lang = (request.query_params.get("lang") or "uz").strip().lower()
        if lang not in {"uz", "ru", "en"}:
            lang = "uz"

        try:
            lesson = Lesson.objects.get(pk=lesson_id)
        except (Lesson.DoesNotExist, ValueError, TypeError):
            return Response(
                {"success": False, "message": "Dars topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        questions = (
            Question.objects.filter(lesson=lesson)
            .order_by("id")
        )
        items = [question_to_frontend(q, lang) for q in questions]

        return Response(
            {
                "success": True,
                "message": "Savollar olindi.",
                "data": {
                    "lesson_id": lesson.id,
                    "questions": items,
                },
            },
            status=status.HTTP_200_OK,
        )

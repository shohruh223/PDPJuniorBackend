from django.db import transaction
from django.db.models import Count, Prefetch

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.models.question import Course, Lesson, Module
from app.models.test import TestSession, TestSessionQuestion, TestSessionAnswer
from app.permissions import IsStudentUserRole
from app.serializers.test import (
    StartTestSessionSerializer,
    StartTestSessionResponseSerializer,
    TestSessionSerializer,
    SessionQuestionSerializer,
    SubmitAnswerSerializer,
    SubmitAnswerResponseSerializer,
    TestSessionResultSerializer,
    StudentModuleWithLessonsSerializer,
    pick_lang_value,
)

lang_param = openapi.Parameter(
    "lang",
    openapi.IN_QUERY,
    description="Test tili. Mumkin qiymatlar: uz, ru, en. Agar yuborilmasa default uz ishlaydi.",
    type=openapi.TYPE_STRING,
    enum=["uz", "ru", "en"],
    required=False,
)


class StudentTestBaseAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    def get_student_course(self, user):
        if hasattr(user, "student_profile"):
            profile = user.student_profile

            if profile.course:
                return profile.course

            group_course_name = profile.resolve_course_name_from_group()
            if group_course_name:
                return Course.objects.filter(name__iexact=group_course_name).first()

        return None

    def get_request_language(self, request):
        explicit_lang = request.query_params.get("lang")

        if not explicit_lang and hasattr(request, "data"):
            explicit_lang = request.data.get("lang")

        if explicit_lang:
            explicit_lang = explicit_lang.strip().lower()
            if explicit_lang in {"uz", "ru", "en"}:
                return explicit_lang

        user_lang = (getattr(request.user, "preferred_language", "") or "").strip().lower()
        if user_lang in {"uz", "ru", "en"}:
            return user_lang

        return "uz"

    def get_session_or_response(self, session_id, user):
        session = (
            TestSession.objects.filter(session_id=session_id, student=user)
            .select_related("lesson", "lesson__course", "lesson__module")
            .prefetch_related("items__question", "answers")
            .first()
        )

        if not session:
            return None, Response(
                {
                    "success": False,
                    "message": "Session topilmadi.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not session.is_finished and session.is_expired():
            session.finish()

        return session, None


class StudentAvailableLessonsAPIView(StudentTestBaseAPIView):
    @swagger_auto_schema(
        tags=["Student Tests"],
        operation_summary="Student uchun test topshirish mumkin bo‘lgan modul va lessonlar ro‘yxati",
        operation_description="""
        Bu endpoint studentga tegishli course bo‘yicha barcha modullar va ularning ichidagi
        lessonlar ro‘yxatini qaytaradi.

        Frontend qanday ishlatadi:
        1. Student login bo‘ladi.
        2. Test bo‘limi ochilganda front shu endpointni chaqiradi.
        3. Response ichidagi `modules` dan testga kirish mumkin bo‘lgan lessonlar ro‘yxati olinadi.
        4. Foydalanuvchi bitta lesson tanlaydi.
        5. Keyingi bosqichda `POST /api/student/tests/start/` endpointi chaqiriladi.

        Ketma-ketlik:
        - login bo‘lgandan keyin test bo‘limida odatda birinchi chaqiriladigan endpoint shu
        - undan keyin:
          `GET /api/student/tests/lessons`
          -> `POST /api/student/tests/start/`

        Auth:
        - faqat login bo‘lgan student foydalanuvchi ishlata oladi
        - `Authorization: Bearer <access_token>` yuborilishi kerak

        Success response:
        - `course`: studentga tegishli course ma’lumoti
        - `modules`: course ichidagi modullar ro‘yxati
        - har bir modul ichida lessonlar ro‘yxati qaytadi
        - har bir lesson ichida odatda test savollari soni ham bo‘ladi

        Muhim:
        - bu endpoint testni boshlamaydi
        - bu endpoint faqat testga kirish uchun lessonlar ro‘yxatini beradi
        """,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Student uchun mavjud modul va lessonlar muvaffaqiyatli olindi.",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Student uchun mavjud lessonlar olindi.",
                        "data": {
                            "course": {
                                "id": 1,
                                "name": "Junior Backend",
                            },
                            "modules": [
                                {
                                    "id": 10,
                                    "name": "Python Basics",
                                    "order": 1,
                                    "lessons_count": 1,
                                    "lessons": [
                                        {
                                            "id": 101,
                                            "name": "Variables",
                                            "order": 1,
                                            "questions_count": 10,
                                            "estimated_duration_minutes": 11,
                                        }
                                    ],
                                }
                            ],
                        },
                    }
                },
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Student uchun mos course topilmadi."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        course = self.get_student_course(request.user)

        if not course:
            return Response(
                {
                    "success": False,
                    "message": "Student uchun mos course topilmadi.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        lessons_qs = (
            Lesson.objects.filter(course=course)
            .annotate(questions_count=Count("questions"))
            .order_by("order", "id")
        )

        modules = (
            Module.objects.filter(course=course)
            .order_by("order", "id")
            .prefetch_related(
                Prefetch(
                    "lessons",
                    queryset=lessons_qs,
                    to_attr="prefetched_lessons",
                )
            )
        )

        serializer = StudentModuleWithLessonsSerializer(modules, many=True)

        return Response(
            {
                "success": True,
                "message": "Student uchun mavjud lessonlar olindi.",
                "data": {
                    "course": {
                        "id": course.id,
                        "name": course.name,
                    },
                    "modules": serializer.data,
                },
            },
            status=status.HTTP_200_OK,
        )


class StartTestSessionAPIView(StudentTestBaseAPIView):
    @swagger_auto_schema(
        tags=["Student Tests"],
        operation_summary="Test session boshlash",
        operation_description="""
        Bu endpoint tanlangan lesson bo‘yicha yangi test session yaratadi
        va shu testga tegishli savollarni qaytaradi.

        Frontend qanday ishlatadi:
        1. Front `GET /api/student/tests/lessons` endpointidan lesson tanlaydi.
        2. Tanlangan lesson `lesson_id` bilan shu endpointga yuboriladi.
        3. Backend yangi session yaratadi.
        4. Response ichida `session` va test savollari qaytadi.
        5. Front test UI ni ochadi va timer/start holatini shu response asosida boshlaydi.

        Ketma-ketlik:
        - `GET /api/student/tests/lessons` dan keyin ishlatiladi
        - undan keyin odatda javob yuborish boshlanadi:
          `POST /api/student/tests/start/`
          -> `POST /api/student/tests/during/{session_id}/answer/`
        - agar foydalanuvchi testni tark etib qaytsa:
          `GET /api/student/tests/during/{session_id}/`

        Qo‘shimcha:
        - `lang` query param orqali savollar tilini tanlash mumkin: `uz`, `ru`, `en`
        - agar `lang` yuborilmasa foydalanuvchi tili yoki default `uz` ishlatiladi

        Auth:
        - faqat login bo‘lgan student foydalanuvchi ishlata oladi

        Request body:
        - `lesson_id`: test boshlanadigan lesson ID si
        - `module_id`: ixtiyoriy, agar frontend modul context bilan yubormoqchi bo‘lsa
        - `lang`: ixtiyoriy, request body yoki query ichida kelishi mumkin

        Success response:
        - `session`: yaratilgan test session ma’lumoti
        - `questions`: test savollari ro‘yxati

        Muhim:
        - testni real boshlash aynan shu endpointda bo‘ladi
        - keyingi barcha javoblar shu session bilan ishlaydi
        """,
        manual_parameters=[lang_param],
        request_body=StartTestSessionSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="Test session muvaffaqiyatli yaratildi va savollar qaytarildi.",
                schema=StartTestSessionResponseSerializer(),
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Request body noto‘g‘ri yoki lesson bo‘yicha session yaratib bo‘lmadi."
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
        },
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = StartTestSessionSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        session = serializer.save()

        items = (
            TestSessionQuestion.objects.select_related("question")
            .filter(session=session)
            .order_by("order")
        )

        lang = self.get_request_language(request)

        response_serializer = StartTestSessionResponseSerializer(
            {
                "session": session,
                "questions": items,
            },
            context={"language": lang},
        )

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TestSessionDetailAPIView(StudentTestBaseAPIView):
    @swagger_auto_schema(
        tags=["Student Tests"],
        operation_summary="Boshlangan test session detailini olish",
        operation_description="""
        Bu endpoint allaqachon boshlangan test session ma’lumotlarini va uning savollarini qaytaradi.

        Frontend qanday ishlatadi:
        1. Student testni boshlab bo‘lgan bo‘ladi.
        2. Front `session_id` ni saqlab qo‘ygan bo‘ladi.
        3. Agar foydalanuvchi sahifani refresh qilsa yoki testga qaytib kirsa,
           shu endpoint orqali session holati qayta olinadi.
        4. Front response asosida testni davom ettiradi.

        Ketma-ketlik:
        - odatda `POST /api/student/tests/start/` dan keyin ishlatiladi
        - ayniqsa refresh yoki resume holatlarida kerak bo‘ladi
        - undan keyin yana javob yuborish davom etadi:
          `GET /api/student/tests/during/{session_id}/`
          -> `POST /api/student/tests/during/{session_id}/answer/`

        Auth:
        - faqat session egasi bo‘lgan login qilgan student ishlata oladi

        Path param:
        - `session_id`: test session UUID si

        Success response:
        - `session`: session holati
        - `questions`: shu sessiondagi savollar ro‘yxati

        Muhim:
        - agar session vaqti tugagan bo‘lsa, backend uni avtomatik finish qilishi mumkin
        - bu endpoint yangi session yaratmaydi
        """,
        manual_parameters=[
            openapi.Parameter(
                "session_id",
                openapi.IN_PATH,
                description="Test session UUID si",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            ),
            lang_param,
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Test session detail muvaffaqiyatli olindi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Session detail olindi.",
                    "data": {
                        "session": {
                            "session_id": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                            "total_questions": 10,
                            "duration_minutes": 11,
                            "remaining_seconds": 540,
                            "answered_count": 2,
                            "is_finished": False,
                        },
                        "questions": [{
                            "id": 1,
                            "order": 1,
                            "question": {
                                "id": 501,
                                "text": "Python ro‘yxati qanday yaratiladi?",
                                "image_url": None,
                                "options": {"A": "[]", "B": "{}"},
                            },
                        }],
                    },
                }},
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Session topilmadi."
            ),
        },
    )
    def get(self, request, session_id, *args, **kwargs):
        session, error_response = self.get_session_or_response(session_id, request.user)
        if error_response:
            return error_response

        items = (
            TestSessionQuestion.objects.select_related("question")
            .filter(session=session)
            .order_by("order")
        )

        lang = self.get_request_language(request)

        return Response(
            {
                "success": True,
                "message": "Session detail olindi.",
                "data": {
                    "session": TestSessionSerializer(session).data,
                    "questions": SessionQuestionSerializer(
                        items,
                        many=True,
                        context={"language": lang},
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )


class SubmitAnswerAPIView(StudentTestBaseAPIView):
    @swagger_auto_schema(
        tags=["Student Tests"],
        operation_summary="Test savoliga javob yuborish",
        operation_description="""
        Bu endpoint test davomida bitta savolga foydalanuvchi tanlagan javobni yuboradi.

        Frontend qanday ishlatadi:
        1. Test session yaratilgan bo‘ladi.
        2. Har safar foydalanuvchi variant tanlaganda shu endpoint chaqiriladi.
        3. Backend javobni saqlaydi.
        4. Response ichida:
           - javob to‘g‘rimi yoki yo‘qmi
           - agar xato bo‘lsa to‘g‘ri javob
           - test tugagan yoki tugamagan holati
           - qolgan vaqt
           qaytadi
        5. Agar `finished = true` bo‘lsa, keyingi endpoint natija olish endpointi bo‘ladi.

        Ketma-ketlik:
        - `POST /api/student/tests/start/` yoki `GET /api/student/tests/during/{session_id}/` dan keyin ishlatiladi
        - har bir savol uchun qayta-qayta chaqiriladi
        - oxirida:
          `POST /api/student/tests/during/{session_id}/answer/`
          -> `GET /api/student/tests/sessions/{session_id}/result/`

        Auth:
        - faqat session egasi bo‘lgan login qilgan student ishlata oladi

        Path param:
        - `session_id`: test session UUID si

        Request body:
        - odatda `question_id` va `selected_option` yuboriladi

        Success response:
        - `question_id`: qaysi savolga javob yuborilgani
        - `selected_option`: foydalanuvchi tanlagan variant
        - `is_correct`: javob to‘g‘rimi yoki yo‘qmi
        - `correct_option`: to‘g‘ri javob
        - `show_correct_answer`: front to‘g‘ri javobni ko‘rsatishi kerakmi
        - `finished`: test tugagan yoki tugamagan
        - `remaining_seconds`: qolgan vaqt

        Muhim:
        - agar javob noto‘g‘ri bo‘lsa, backend to‘g‘ri javobni ham qaytaradi
        - agar oxirgi savol yuborilgan bo‘lsa session finish bo‘lishi mumkin
        """,
        request_body=SubmitAnswerSerializer,
        manual_parameters=[
            openapi.Parameter(
                "session_id",
                openapi.IN_PATH,
                description="Test session UUID si",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Javob muvaffaqiyatli yuborildi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Javob qabul qilindi.",
                    "data": {
                        "question_id": 501,
                        "selected_option": "A",
                        "is_correct": True,
                        "correct_option": "A",
                        "show_correct_answer": False,
                        "finished": False,
                        "remaining_seconds": 480,
                    },
                }},
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Javob formati noto‘g‘ri yoki session holati sababli javob qabul qilinmadi."
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Session topilmadi."
            ),
        },
    )
    @transaction.atomic
    def post(self, request, session_id, *args, **kwargs):
        session, error_response = self.get_session_or_response(session_id, request.user)
        if error_response:
            return error_response

        serializer = SubmitAnswerSerializer(
            data=request.data,
            context={"session": session},
        )
        serializer.is_valid(raise_exception=True)
        answer = serializer.save()

        total = session.items.count()
        answered = session.answers.count()

        finished = answered >= total
        if finished:
            session.finish()

        question = answer.question
        show_correct_answer = answer.selected_option != question.correct_option

        response_serializer = SubmitAnswerResponseSerializer(
            {
                "question_id": answer.question_id,
                "selected_option": answer.selected_option,
                "is_correct": answer.is_correct,
                "correct_option": question.correct_option,
                "show_correct_answer": show_correct_answer,
                "finished": finished,
                "remaining_seconds": session.remaining_seconds,
            }
        )
        return Response(
            {
                "success": True,
                "message": "Javob qabul qilindi.",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class TestSessionResultAPIView(StudentTestBaseAPIView):
    @swagger_auto_schema(
        tags=["Student Tests"],
        operation_summary="Test natijasini olish",
        operation_description="""
Bu endpoint tugagan yoki yakunlanayotgan test session natijasini qaytaradi.

Frontend qanday ishlatadi:
1. Test davomida barcha javoblar yuboriladi.
2. Oxirgi javobdan keyin yoki vaqt tugagandan keyin
   shu endpoint chaqiriladi.
3. Front response ichidagi natijalar asosida result screen chizadi.

Ketma-ketlik:
- odatda `SubmitAnswerAPIView` dan keyin ishlatiladi
- ayniqsa `finished = true` bo‘lsa darhol shu endpoint chaqiriladi

Auth:
- faqat session egasi bo‘lgan login qilgan student ishlata oladi

Path param:
- `session_id`: test session UUID si

Success response:
- `percent`: to‘g‘ri javoblar foizi
- `spent_time`: testga sarflangan vaqt
- `total`: jami savollar soni
- `correct`: to‘g‘ri javoblar soni
- `wrong`: noto‘g‘ri javoblar soni
- `unanswered`: javobsiz qolgan savollar soni
- `questions`: har bir savol bo‘yicha to‘liq natija

Muhim:
- agar session hali finish bo‘lmagan bo‘lsa, bu endpoint uni finish qilib yuborishi mumkin
- result screen uchun asosiy endpoint shu
""",
        manual_parameters=[
            openapi.Parameter(
                "session_id",
                openapi.IN_PATH,
                description="Test session UUID si",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            ),
            lang_param,
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Test natijasi muvaffaqiyatli olindi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Test natijasi olindi.",
                    "data": {
                        "percent": 80,
                        "spent_time": "8:35",
                        "total": 10,
                        "correct": 8,
                        "wrong": 1,
                        "unanswered": 1,
                        "questions": [{
                            "id": 501,
                            "order": 1,
                            "text": "Python ro‘yxati qanday yaratiladi?",
                            "image_url": None,
                            "options": {"A": "[]", "B": "{}"},
                            "correct_option": "A",
                            "selected_option": "A",
                            "is_correct": True,
                            "is_answered": True,
                        }],
                    },
                }},
            ),
            status.HTTP_401_UNAUTHORIZED: openapi.Response(
                description="Token yuborilmagan yoki token noto‘g‘ri."
            ),
            status.HTTP_403_FORBIDDEN: openapi.Response(
                description="Foydalanuvchida student roli yo‘q."
            ),
            status.HTTP_404_NOT_FOUND: openapi.Response(
                description="Session topilmadi."
            ),
        },
    )
    def get(self, request, session_id, *args, **kwargs):
        session, error_response = self.get_session_or_response(session_id, request.user)
        if error_response:
            return error_response

        if not session.is_finished:
            session.finish()

        lang = self.get_request_language(request)

        items = (
            TestSessionQuestion.objects.select_related("question")
            .filter(session=session)
            .order_by("order")
        )

        answers_map = {
            answer.question_id: answer
            for answer in TestSessionAnswer.objects.filter(session=session)
        }

        correct = 0
        wrong = 0
        unanswered = 0
        result_questions = []

        for item in items:
            question = item.question
            answer = answers_map.get(question.id)

            selected_option = answer.selected_option if answer else None
            is_answered = answer is not None
            is_correct = bool(answer and answer.is_correct)

            if not is_answered:
                unanswered += 1
            elif is_correct:
                correct += 1
            else:
                wrong += 1

            images = question.images or {}
            image_url = None
            if isinstance(images, dict):
                image_url = (
                        images.get(lang)
                        or images.get("uz")
                        or next(iter(images.values()), None)
                )

            result_questions.append(
                {
                    "id": question.id,
                    "order": item.order,
                    "text": pick_lang_value(question.text, lang),
                    "image_url": image_url,
                    "options": {
                        key: pick_lang_value(value, lang)
                        for key, value in (question.options or {}).items()
                    },
                    "correct_option": question.correct_option,
                    "selected_option": selected_option,
                    "is_correct": is_correct,
                    "is_answered": is_answered,
                }
            )

        total = len(result_questions)
        percent = int((correct * 100) / total) if total else 0

        spent_seconds = session.spent_seconds
        spent_time = f"{spent_seconds // 60}:{spent_seconds % 60:02d}"

        serializer = TestSessionResultSerializer(
            {
                "percent": percent,
                "spent_time": spent_time,
                "total": total,
                "correct": correct,
                "wrong": wrong,
                "unanswered": unanswered,
                "questions": result_questions,
            }
        )
        return Response(
            {
                "success": True,
                "message": "Test natijasi olindi.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

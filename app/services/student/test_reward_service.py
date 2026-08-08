from django.db import transaction

from app.models.auth import StudentProfile


@transaction.atomic
def reward_student_for_test(student_profile: StudentProfile, correct_answers_count: int):
    """
    Misol:
    - har bir to‘g‘ri javob = 1 score
    - har bir to‘g‘ri javob = 1 coin
    """
    gained_score = int(correct_answers_count or 0)
    gained_coin = gained_score

    student_profile.local_test_score += gained_score
    student_profile.test_coin += gained_coin
    student_profile.recalculate_all_totals(save=False)

    student_profile.save(
        update_fields=[
            "local_test_score",
            "test_coin",
            "total_score",
            "total_coin",
            "updated_at",
        ]
    )

    return {
        "gained_score": gained_score,
        "gained_coin": gained_coin,
        "local_test_score": student_profile.local_test_score,
        "test_coin": student_profile.test_coin,
        "total_score": student_profile.total_score,
        "total_coin": student_profile.total_coin,
    }
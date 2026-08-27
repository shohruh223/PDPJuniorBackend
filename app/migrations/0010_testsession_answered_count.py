# Generated manually for production performance optimizations.

from django.db import migrations, models
from django.db.models import Count


def backfill_answered_count(apps, schema_editor):
    TestSession = apps.get_model("app", "TestSession")
    sessions = TestSession.objects.annotate(
        answers_total=Count("answers", distinct=True),
    ).filter(answered_count=0, answers_total__gt=0)

    for session in sessions.iterator(chunk_size=500):
        TestSession.objects.filter(pk=session.pk).update(
            answered_count=session.answers_total,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0009_student_invoice"),
    ]

    operations = [
        migrations.AddField(
            model_name="testsession",
            name="answered_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_answered_count, migrations.RunPython.noop),
    ]

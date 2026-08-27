from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0011_testsession_expire_index"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="testsession",
            index=models.Index(
                fields=["student", "lesson", "is_finished"],
                name="test_session_st_lesson_idx",
            ),
        ),
    ]

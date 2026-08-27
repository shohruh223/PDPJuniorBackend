from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0010_testsession_answered_count"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="testsession",
            index=models.Index(
                fields=["is_finished", "expires_at"],
                name="test_session_expire_idx",
            ),
        ),
    ]

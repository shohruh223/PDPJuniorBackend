from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0006_remove_mentor_socials"),
    ]

    operations = [
        migrations.DeleteModel(
            name="News",
        ),
    ]

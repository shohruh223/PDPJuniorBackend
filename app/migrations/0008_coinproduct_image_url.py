from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0007_delete_news"),
    ]

    operations = [
        migrations.AddField(
            model_name="coinproduct",
            name="image_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]

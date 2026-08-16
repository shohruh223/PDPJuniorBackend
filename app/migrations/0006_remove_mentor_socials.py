from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0005_coinorder_admin_read_at_coinorder_balance_after_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="mentor",
            name="socials",
        ),
    ]

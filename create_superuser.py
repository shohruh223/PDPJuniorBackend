import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

phone_number = os.getenv("DJANGO_SUPERUSER_PHONE_NUMBER")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

if not phone_number or not password:
    raise RuntimeError(
        "DJANGO_SUPERUSER_PHONE_NUMBER and DJANGO_SUPERUSER_PASSWORD "
        "environment variables are required."
    )

if not User.objects.filter(phone_number=phone_number).exists():
    User.objects.create_superuser(
        phone_number=phone_number,
        password=password
    )
    print("Superuser created successfully")
else:
    print("Superuser already exists")


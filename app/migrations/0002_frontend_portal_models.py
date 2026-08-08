# Generated manually for frontend portal endpoints

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="coinproduct",
            name="bg_gradient",
            field=models.CharField(
                blank=True,
                default="linear-gradient(135deg,#ff2fd5,#7c3aed)",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="coinproduct",
            name="category",
            field=models.CharField(
                choices=[
                    ("academy", "Maktab"),
                    ("gadget", "Gadjetlar"),
                    ("book", "Kitoblar"),
                    ("special", "Maxsus"),
                ],
                db_index=True,
                default="academy",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="coinproduct",
            name="emoji",
            field=models.CharField(default="🎁", max_length=16),
        ),
        migrations.AddField(
            model_name="coinproduct",
            name="stock",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="GalleryPost",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.JSONField()),
                ("icon", models.CharField(default="📰", max_length=16)),
                ("date", models.CharField(max_length=20)),
                ("views_count", models.PositiveIntegerField(default=0)),
                ("views_display", models.CharField(blank=True, default="", max_length=20)),
                ("cover_image", models.CharField(blank=True, default="", max_length=500)),
                ("cover_contain", models.BooleanField(default=False)),
                ("cover_bg", models.CharField(blank=True, default="", max_length=200)),
                ("title", models.JSONField()),
                ("description", models.JSONField()),
                ("media", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Galereya posti",
                "verbose_name_plural": "Galereya postlari",
                "db_table": "gallery_posts",
                "ordering": ["sort_order", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CoinOrder",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product_title", models.CharField(max_length=120)),
                ("price", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Kutilmoqda"),
                            ("completed", "Bajarildi"),
                            ("cancelled", "Bekor qilindi"),
                        ],
                        db_index=True,
                        default="completed",
                        max_length=20,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="orders",
                        to="app.coinproduct",
                    ),
                ),
                (
                    "student_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coin_orders",
                        to="app.studentprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Coin buyurtma",
                "verbose_name_plural": "Coin buyurtmalar",
                "db_table": "coin_orders",
                "ordering": ["-created_at"],
            },
        ),
    ]

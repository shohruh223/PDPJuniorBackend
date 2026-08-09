from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions

from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf.urls.i18n import i18n_patterns


class DocumentedTokenObtainPairView(TokenObtainPairView):
    @swagger_auto_schema(
        tags=["Autentifikatsiya / JWT"],
        operation_summary="JWT token olish",
        operation_description=(
            "Foydalanuvchi login ma'lumotlari orqali `access` va `refresh` tokenlarini oladi.\n\n"
            "**Ishlatish:** request body ichida `phone_number` va `password` yuboring. "
            "Himoyalangan endpointlarda qaytgan access tokenni "
            "`Authorization: Bearer <access_token>` headerida yuboring.\n\n"
            "`access` token muddati tugasa, `/api/token/refresh/` endpointiga "
            "`refresh` tokenni yuborib yangi access token oling."
        ),
        responses={
            200: openapi.Response(
                description="Tokenlar muvaffaqiyatli yaratildi.",
                examples={
                    "application/json": {
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                    }
                },
            ),
            401: openapi.Response(description="Login ma'lumotlari noto'g'ri."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenRefreshView(TokenRefreshView):
    @swagger_auto_schema(
        tags=["Autentifikatsiya / JWT"],
        operation_summary="Access tokenni yangilash",
        operation_description=(
            "Muddati tugagan access token o'rniga yangi token qaytaradi.\n\n"
            "**Ishlatish:** login vaqtida olingan `refresh` tokenni request body ichida "
            "yuboring. Sozlamada token rotatsiyasi yoqilganligi sababli javobda yangi "
            "`refresh` token ham kelishi mumkin; keyingi yangilashda eng oxirgi tokenni ishlating."
        ),
        responses={
            200: openapi.Response(
                description="Yangi tokenlar yaratildi.",
                examples={
                    "application/json": {
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                    }
                },
            ),
            401: openapi.Response(description="Refresh token yaroqsiz yoki muddati tugagan."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


schema_view = get_schema_view(
    openapi.Info(
        title="PDP Junior API",
        default_version='v1',
        description=(
            "PDP Junior backend endpointlari.\n\n"
            "**Himoyalangan API'lardan foydalanish:** avval autentifikatsiya endpointi "
            "orqali access token oling. Swagger oynasidagi **Authorize** tugmasini bosib "
            "`Bearer <access_token>` ko'rinishida kiriting. Public deb ko'rsatilgan "
            "endpointlar tokensiz ishlaydi."
        ),
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', include('app.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path("api/token/", DocumentedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", DocumentedTokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

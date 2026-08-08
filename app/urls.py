from django.urls import path

from app.views.auth_view import (
    EnterPasswordAPIView,
    CheckSMSCodeAPIView,
    ForgotPasswordAPIView,
    VerifySMSCodeAPIView,
    SetNewPasswordAPIView,
)
from app.views.frontend_auth_view import (
    FrontendLoginAPIView,
    FrontendVerifyLoginAPIView,
    FrontendForgotPasswordAPIView,
    FrontendVerifyForgotPasswordAPIView,
    FrontendResetPasswordAPIView,
    FrontendResendSmsAPIView,
)
from app.views.mentor import MentorListAPIView
from app.views.month_hero import MonthHeroListAPIView
from app.views.news import NewsListAPIView, PublicNewsListAPIView
from app.views.payment import StudentPaymentHistoryListAPIView
from app.views.portfolio import PortfolioListAPIView
from app.views.profile import (
    StudentProfileImageUpdateAPIView,
    StudentPasswordChangeAPIView,
    StudentProfileAPIView,
)
from app.views.student_dashboard_view import StudentDashboardAPIView
from app.views.lesson_questions_view import LessonQuestionsAPIView
from app.views.test import (
    StudentAvailableLessonsAPIView,
    StartTestSessionAPIView,
    TestSessionDetailAPIView,
    SubmitAnswerAPIView,
    TestSessionResultAPIView,
)
from app.views.coin import (
    StudentCoinProductListAPIView,
    StudentCoinProductDetailAPIView,
)
from app.views.branch import BranchListAPIView
from app.views.ranking import RankingListAPIView, StudentRankingMeAPIView
from app.views.gallery import GalleryListAPIView, GalleryDetailAPIView
from app.views.heroes_portal import HeroesPortalAPIView
from app.views.shop import (
    ShopCatalogAPIView,
    ShopBalanceAPIView,
    ShopProductDetailAPIView,
    ShopOrderListAPIView,
    ShopOrderCreateAPIView,
)
from app.views.modules_lessons import (
    ModuleListAPIView,
    ModuleDetailAPIView,
    LessonListAPIView,
    LessonDetailAPIView,
)
from app.views.catalog import CourseCatalogAPIView
from app.views.marks import StudentMarksAPIView
urlpatterns = [
    # ── Frontend auth (PDP Junior portal) ──────────────────────────────────
    path("auth/login", FrontendLoginAPIView.as_view(), name="frontend-login"),
    path("auth/login/verify", FrontendVerifyLoginAPIView.as_view(), name="frontend-login-verify"),
    path("auth/forgot-password", FrontendForgotPasswordAPIView.as_view(), name="frontend-forgot-password"),
    path(
        "auth/forgot-password/verify",
        FrontendVerifyForgotPasswordAPIView.as_view(),
        name="frontend-forgot-password-verify",
    ),
    path("auth/reset-password", FrontendResetPasswordAPIView.as_view(), name="frontend-reset-password"),
    path("auth/sms/resend", FrontendResendSmsAPIView.as_view(), name="frontend-resend-sms"),

    # ── Student API (/api/student/...) — frontend kontrakt ───────────────────
    path("api/student/dashboard", StudentDashboardAPIView.as_view(), name="api-student-dashboard"),
    path("api/student/profile", StudentProfileAPIView.as_view(), name="api-student-profile"),
    path(
        "api/student/profile/image/",
        StudentProfileImageUpdateAPIView.as_view(),
        name="api-student-profile-image",
    ),
    path(
        "api/student/profile/password/",
        StudentPasswordChangeAPIView.as_view(),
        name="api-student-profile-password",
    ),
    path("api/student/news", NewsListAPIView.as_view(), name="api-student-news"),
    path("api/student/coin-products", StudentCoinProductListAPIView.as_view(), name="api-student-coin-products"),
    path(
        "api/student/coin-products/<uuid:id>/",
        StudentCoinProductDetailAPIView.as_view(),
        name="api-student-coin-product-detail",
    ),
    path(
        "api/student/payment-histories",
        StudentPaymentHistoryListAPIView.as_view(),
        name="api-student-payment-histories",
    ),
    path("api/student/marks", StudentMarksAPIView.as_view(), name="api-student-marks"),
    # Darslar va testlar
    path("api/student/tests/lessons", StudentAvailableLessonsAPIView.as_view(), name="api-student-test-lessons"),
    path("api/student/tests/start/", StartTestSessionAPIView.as_view(), name="api-student-test-start"),
    path(
        "api/student/tests/during/<uuid:session_id>/",
        TestSessionDetailAPIView.as_view(),
        name="api-student-test-during",
    ),
    path(
        "api/student/tests/during/<uuid:session_id>/answer/",
        SubmitAnswerAPIView.as_view(),
        name="api-student-test-answer",
    ),
    path(
        "api/student/tests/sessions/<uuid:session_id>/result/",
        TestSessionResultAPIView.as_view(),
        name="api-student-test-result",
    ),
    path(
        "api/student/lessons/<int:lesson_id>/questions",
        LessonQuestionsAPIView.as_view(),
        name="api-student-lesson-questions",
    ),
    # Modullar va darslar (frontend lessons-data.js)
    path("api/student/modules", ModuleListAPIView.as_view(), name="api-student-modules"),
    path("api/student/modules/<int:module_id>/", ModuleDetailAPIView.as_view(), name="api-student-module-detail"),
    path("api/student/lessons", LessonListAPIView.as_view(), name="api-student-lessons"),
    path("api/student/lessons/<int:lesson_id>/", LessonDetailAPIView.as_view(), name="api-student-lesson-detail"),

    # Reyting (frontend ranking-page.js)
    path("api/ranking", RankingListAPIView.as_view(), name="api-ranking"),
    path("api/student/ranking/me", StudentRankingMeAPIView.as_view(), name="api-student-ranking-me"),

    # Do‘kon (frontend shop.html)
    path("api/student/shop", ShopCatalogAPIView.as_view(), name="api-student-shop"),
    path("api/student/shop/balance", ShopBalanceAPIView.as_view(), name="api-student-shop-balance"),
    path("api/student/shop/orders", ShopOrderListAPIView.as_view(), name="api-student-shop-orders"),
    path("api/student/shop/orders/create/", ShopOrderCreateAPIView.as_view(), name="api-student-shop-order-create"),
    path(
        "api/student/shop/products/<uuid:product_id>/",
        ShopProductDetailAPIView.as_view(),
        name="api-student-shop-product-detail",
    ),

    # ── Public API ─────────────────────────────────────────────────────────
    path("api/courses", CourseCatalogAPIView.as_view(), name="api-courses"),
    path("api/gallery", GalleryListAPIView.as_view(), name="api-gallery"),
    path("api/gallery/<uuid:post_id>/", GalleryDetailAPIView.as_view(), name="api-gallery-detail"),
    path("api/heroes", HeroesPortalAPIView.as_view(), name="api-heroes"),
    path("api/branches", BranchListAPIView.as_view(), name="api-branches"),
    path("api/mentors", MentorListAPIView.as_view(), name="api-mentors"),
    path("api/portfolios", PortfolioListAPIView.as_view(), name="api-portfolios"),
    path("api/month-heroes", MonthHeroListAPIView.as_view(), name="api-month-heroes"),
    path("api/news", PublicNewsListAPIView.as_view(), name="api-news"),
]


def _hidden_view(view_class):
    """Compatibility URL ishlaydi, ammo Swagger'da takroran ko'rinmaydi."""
    hidden_class = type(
        f"SwaggerHidden{view_class.__name__}",
        (view_class,),
        {"swagger_schema": None, "__module__": view_class.__module__},
    )
    return hidden_class.as_view()


# Slash bilan yozilgan va eski frontend URL'lari orqaga moslik uchun saqlanadi.
# Ular yuqoridagi canonical endpointlar bilan bir xil ishlaydi, lekin Swagger
# hujjatida API'ni ikki marta ko'rsatmaslik uchun yashirilgan.
urlpatterns += [
    # Canonical URL'larning trailing-slash aliaslari
    path("auth/login/", _hidden_view(FrontendLoginAPIView), name="compat-frontend-login-slash"),
    path("auth/login/verify/", _hidden_view(FrontendVerifyLoginAPIView), name="compat-frontend-login-verify-slash"),
    path("auth/forgot-password/", _hidden_view(FrontendForgotPasswordAPIView), name="compat-frontend-forgot-password-slash"),
    path(
        "auth/forgot-password/verify/",
        _hidden_view(FrontendVerifyForgotPasswordAPIView),
        name="compat-frontend-forgot-password-verify-slash",
    ),
    path("auth/reset-password/", _hidden_view(FrontendResetPasswordAPIView), name="compat-frontend-reset-password-slash"),
    path("auth/sms/resend/", _hidden_view(FrontendResendSmsAPIView), name="compat-frontend-resend-sms-slash"),
    path("api/student/dashboard/", _hidden_view(StudentDashboardAPIView), name="compat-api-student-dashboard-slash"),
    path("api/student/profile/", _hidden_view(StudentProfileAPIView), name="compat-api-student-profile-slash"),
    path("api/student/news/", _hidden_view(NewsListAPIView), name="compat-api-student-news-slash"),
    path("api/student/marks/", _hidden_view(StudentMarksAPIView), name="compat-api-student-marks-slash"),
    path(
        "api/student/coin-products/",
        _hidden_view(StudentCoinProductListAPIView),
        name="compat-api-student-coin-products-slash",
    ),
    path(
        "api/student/payment-histories/",
        _hidden_view(StudentPaymentHistoryListAPIView),
        name="compat-api-student-payment-histories-slash",
    ),
    path(
        "api/student/month-heroes/",
        _hidden_view(MonthHeroListAPIView),
        name="compat-api-student-month-heroes-slash",
    ),
    path(
        "api/student/tests/lessons/",
        _hidden_view(StudentAvailableLessonsAPIView),
        name="compat-api-student-test-lessons-slash",
    ),
    path(
        "api/student/lessons/<int:lesson_id>/questions/",
        _hidden_view(LessonQuestionsAPIView),
        name="compat-api-student-lesson-questions-slash",
    ),
    path("api/student/modules/", _hidden_view(ModuleListAPIView), name="compat-api-student-modules-slash"),
    path("api/student/lessons/", _hidden_view(LessonListAPIView), name="compat-api-student-lessons-slash"),
    path("api/ranking/", _hidden_view(RankingListAPIView), name="compat-api-ranking-slash"),
    path(
        "api/student/ranking/",
        _hidden_view(RankingListAPIView),
        name="compat-api-student-ranking",
    ),
    path(
        "api/student/ranking/me/",
        _hidden_view(StudentRankingMeAPIView),
        name="compat-api-student-ranking-me-slash",
    ),
    path("api/student/shop/", _hidden_view(ShopCatalogAPIView), name="compat-api-student-shop-slash"),
    path(
        "api/student/shop/balance/",
        _hidden_view(ShopBalanceAPIView),
        name="compat-api-student-shop-balance-slash",
    ),
    path(
        "api/student/shop/orders/",
        _hidden_view(ShopOrderListAPIView),
        name="compat-api-student-shop-orders-slash",
    ),
    path("api/courses/", _hidden_view(CourseCatalogAPIView), name="compat-api-courses-slash"),
    path("api/gallery/", _hidden_view(GalleryListAPIView), name="compat-api-gallery-slash"),
    path("api/heroes/", _hidden_view(HeroesPortalAPIView), name="compat-api-heroes-slash"),
    path("api/branches/", _hidden_view(BranchListAPIView), name="compat-api-branches-slash"),
    path("api/mentors/", _hidden_view(MentorListAPIView), name="compat-api-mentors-slash"),
    path("api/portfolios/", _hidden_view(PortfolioListAPIView), name="compat-api-portfolios-slash"),
    path("api/month-heroes/", _hidden_view(MonthHeroListAPIView), name="compat-api-month-heroes-slash"),
    path("api/news/", _hidden_view(PublicNewsListAPIView), name="compat-api-news-slash"),

    # Eski auth va student integratsiyalari
    path("auth/enter-password/", _hidden_view(EnterPasswordAPIView), name="compat-enter-password"),
    path("auth/check-sms-code/", _hidden_view(CheckSMSCodeAPIView), name="compat-check-sms-code"),
    path("auth/forgot-password/", _hidden_view(ForgotPasswordAPIView), name="compat-forgot-password"),
    path("auth/verify-sms-code/", _hidden_view(VerifySMSCodeAPIView), name="compat-verify-sms-code"),
    path("auth/set-new-password/", _hidden_view(SetNewPasswordAPIView), name="compat-set-new-password"),
    path("student/dashboard/", _hidden_view(StudentDashboardAPIView), name="compat-student-dashboard"),
    path("student/profile/", _hidden_view(StudentProfileAPIView), name="compat-student-profile"),
    path(
        "student/profile/image/",
        _hidden_view(StudentProfileImageUpdateAPIView),
        name="compat-student-profile-image-update",
    ),
    path(
        "student/profile/password/",
        _hidden_view(StudentPasswordChangeAPIView),
        name="compat-student-password-change",
    ),
    path("student/news/", _hidden_view(NewsListAPIView), name="compat-news-list"),
    path(
        "student/coin-products/",
        _hidden_view(StudentCoinProductListAPIView),
        name="compat-student-coin-products",
    ),
    path(
        "student/coin-products/<uuid:id>/",
        _hidden_view(StudentCoinProductDetailAPIView),
        name="compat-student-coin-product-detail",
    ),
    path(
        "student/payment-histories/",
        _hidden_view(StudentPaymentHistoryListAPIView),
        name="compat-student-payment-histories",
    ),
    path("student/month-heroes/", _hidden_view(MonthHeroListAPIView), name="compat-month-heroes"),
    path(
        "student/tests/lessons/",
        _hidden_view(StudentAvailableLessonsAPIView),
        name="compat-student-test-lessons",
    ),
    path("student/tests/start/", _hidden_view(StartTestSessionAPIView), name="compat-student-test-start"),
    path(
        "student/tests/during/<uuid:session_id>/",
        _hidden_view(TestSessionDetailAPIView),
        name="compat-student-test-during",
    ),
    path(
        "student/tests/during/<uuid:session_id>/answer/",
        _hidden_view(SubmitAnswerAPIView),
        name="compat-student-test-answer",
    ),
    path(
        "student/tests/sessions/<uuid:session_id>/result/",
        _hidden_view(TestSessionResultAPIView),
        name="compat-student-test-result",
    ),

    # Eski public aliaslar
    path("branches/", _hidden_view(BranchListAPIView), name="compat-branch-list"),
    path("mentors/", _hidden_view(MentorListAPIView), name="compat-mentor-list"),
    path("portfolios/", _hidden_view(PortfolioListAPIView), name="compat-portfolio-list"),
]

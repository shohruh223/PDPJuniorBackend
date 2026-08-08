from rest_framework.permissions import BasePermission

from app.models import User


class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.RoleChoices.ADMIN
        )


class IsStudentUserRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.RoleChoices.STUDENT
        )


class IsStudent(BasePermission):
    message = "Faqat studentlar uchun ruxsat berilgan."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_student", False)
        )
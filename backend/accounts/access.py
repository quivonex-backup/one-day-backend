from rest_framework.permissions import BasePermission


def is_admin(user):
    """Only Django staff or superusers can access administration APIs."""
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


class IsAdmin(BasePermission):
    """DRF permission for admin-only APIs."""
    message = "Admin access required."

    def has_permission(self, request, view):
        return is_admin(request.user)
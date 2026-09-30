from rest_framework.permissions import SAFE_METHODS, BasePermission


def user_is_admin(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or (
        getattr(user, 'rol', None) is not None and user.rol.nombre == 'ADMIN'
    )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or user_is_admin(request.user)


class CanCreateOrder(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method != 'POST':
            return True
        return user_is_admin(user) or (
            getattr(user, 'rol', None) is not None and user.rol.nombre == 'CLIENTE'
        )
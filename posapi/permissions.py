from rest_framework.permissions import BasePermission


class IsKasirAktif(BasePermission):
    """User harus punya userprofile aktif (bukan staff / owner korporasi)."""
    message = 'Akun tidak aktif atau bukan kasir toko.'

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and u.is_active) or u.is_staff:
            return False
        profile = getattr(u, 'userprofile', None)
        return bool(profile and profile.is_active and profile.cabang.is_active)

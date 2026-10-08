import datetime

from django.conf import settings

from posmimail import posmiMail


def kirim_verifikasi_email(cabang, base_url=None):
    """Buat token baru (token lama dihapus) dan kirim link verifikasi ke email toko."""
    from cms.models import EmailVerificationToken
    EmailVerificationToken.objects.filter(cabang=cabang).delete()
    ev_token = EmailVerificationToken.objects.create(
        cabang=cabang,
        expired_at=datetime.datetime.now() + datetime.timedelta(hours=48)
    )
    base_url = (base_url or settings.SITE_URL).rstrip('/')
    verify_url = f"{base_url}/cms/verifikasi-email/{ev_token.token}/"
    return posmiMail(
        "Verifikasi Email POSMI",
        f"Klik link berikut untuk verifikasi email toko Anda (berlaku 48 jam). "
        f"Setelah terverifikasi, Anda baru bisa login:\n{verify_url}\n\n— Tim POSMI",
        address=cabang.email
    )

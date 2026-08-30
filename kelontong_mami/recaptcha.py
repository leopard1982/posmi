import requests
from django.conf import settings

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_recaptcha(request, action=None):
    """Verifikasi token reCAPTCHA v3 yang dikirim form via field g_recaptcha_response.

    Return True jika token valid, cocok dengan action (bila diberikan), dan skor
    >= RECAPTCHA_MIN_SCORE. Return False untuk semua kondisi lain (termasuk error
    jaringan ke Google), supaya gagal aman (fail closed).
    """
    token = request.POST.get('g_recaptcha_response', '')
    if not token:
        return False
    try:
        response = requests.post(
            RECAPTCHA_VERIFY_URL,
            data={
                'secret': settings.RECAPTCHA_SECRET_KEY,
                'response': token,
                'remoteip': request.META.get('REMOTE_ADDR', ''),
            },
            timeout=5,
        )
        result = response.json()
    except Exception:
        return False

    if not result.get('success'):
        return False
    if action and result.get('action') != action:
        return False
    return result.get('score', 0) >= settings.RECAPTCHA_MIN_SCORE

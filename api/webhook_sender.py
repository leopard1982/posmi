"""
Kirim notifikasi ke webhook URL ketika event terjadi di POSMI.
Dipanggil dari views lain (pos, cms) setelah event terjadi.
"""
import json, hmac, hashlib, datetime


def send_webhook(cabang, event, payload: dict):
    """
    Kirim payload JSON ke semua webhook endpoint yang terdaftar untuk event ini.
    Signed dengan HMAC-SHA256 menggunakan secret webhook.
    """
    try:
        import requests
        from .models import WebhookEndpoint, WebhookLog

        hooks = WebhookEndpoint.objects.filter(
            cabang=cabang, event=event, is_active=True
        )
        if not hooks.exists():
            return

        body = json.dumps({
            'event': event,
            'timestamp': datetime.datetime.now().isoformat(),
            'kode_toko': cabang.prefix,
            'data': payload,
        }, ensure_ascii=False)

        for hook in hooks:
            signature = hmac.new(
                hook.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            try:
                resp = requests.post(
                    hook.url,
                    data=body,
                    headers={
                        'Content-Type': 'application/json',
                        'X-POSMI-Event': event,
                        'X-POSMI-Signature': f'sha256={signature}',
                    },
                    timeout=10
                )
                WebhookLog.objects.create(
                    webhook=hook, event=event, payload=payload,
                    status=WebhookLog.STATUS_OK if resp.ok else WebhookLog.STATUS_FAIL,
                    response_code=resp.status_code,
                )
            except Exception as e:
                WebhookLog.objects.create(
                    webhook=hook, event=event, payload=payload,
                    status=WebhookLog.STATUS_FAIL, error=str(e),
                )
    except Exception:
        pass  # Jangan crash aplikasi utama jika webhook gagal

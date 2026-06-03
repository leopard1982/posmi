import json, hmac, hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from .models import ApiKey


# ── Auth helper ──────────────────────────────────────────────────────────────

def _authenticate(request):
    """Validate Bearer token from Authorization header. Returns Cabang or None."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[7:].strip()
    try:
        ak = ApiKey.objects.select_related('cabang').get(key=token, is_active=True)
        ak.last_used = timezone.now()
        ak.save(update_fields=['last_used'])
        return ak.cabang
    except ApiKey.DoesNotExist:
        return None


def _err(msg, status=400):
    return JsonResponse({'success': False, 'error': msg}, status=status)


def _ok(data, **meta):
    return JsonResponse({'success': True, **meta, 'data': data})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
def api_transactions(request):
    """
    GET /api/v1/transactions/
    Query params: page (int), per_page (int, max 100), bulan (YYYY-MM)
    """
    cabang = _authenticate(request)
    if not cabang:
        return _err('Unauthorized. Sertakan header: Authorization: Bearer <api_key>', 401)

    from pos.models import Penjualan
    import datetime

    qs = Penjualan.objects.filter(cabang=cabang, is_paid=True, is_void=False).order_by('-tgl_bayar')

    # Filter bulan
    bulan_str = request.GET.get('bulan')
    if bulan_str:
        try:
            dt = datetime.datetime.strptime(bulan_str, '%Y-%m')
            qs = qs.filter(tgl_bayar__year=dt.year, tgl_bayar__month=dt.month)
        except ValueError:
            return _err("Format bulan: YYYY-MM (contoh: 2026-06)")

    total = qs.count()
    per_page = min(int(request.GET.get('per_page', 25)), 100)
    page = max(1, int(request.GET.get('page', 1)))
    offset = (page - 1) * per_page
    qs = qs[offset:offset + per_page]

    items = []
    for t in qs:
        items.append({
            'nota': t.nota,
            'no_nota': t.no_nota,
            'tanggal': t.tgl_bayar.isoformat() if t.tgl_bayar else None,
            'total': int(t.total),
            'metode': 'cash' if t.metode == 0 else 'transfer',
            'customer': t.customer or '',
        })

    return _ok(items, total=total, page=page, per_page=per_page,
               pages=max(1, (total + per_page - 1) // per_page))


@csrf_exempt
@require_http_methods(['GET'])
def api_products(request):
    """
    GET /api/v1/products/
    Query params: page, per_page, search (nama/barcode)
    """
    cabang = _authenticate(request)
    if not cabang:
        return _err('Unauthorized', 401)

    from stock.models import Barang
    qs = Barang.objects.filter(cabang=cabang).order_by('nama')

    q = request.GET.get('search', '').strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(nama__icontains=q) | Q(barcode__icontains=q))

    total = qs.count()
    per_page = min(int(request.GET.get('per_page', 50)), 100)
    page = max(1, int(request.GET.get('page', 1)))
    offset = (page - 1) * per_page
    qs = qs[offset:offset + per_page]

    items = [{
        'id': b.id,
        'barcode': b.barcode,
        'nama': b.nama,
        'satuan': b.satuan,
        'stok': b.stok,
        'harga_ecer': b.harga_ecer,
        'harga_grosir': b.harga_grosir,
        'harga_beli': b.harga_beli,
    } for b in qs]

    return _ok(items, total=total, page=page, per_page=per_page,
               pages=max(1, (total + per_page - 1) // per_page))


@csrf_exempt
@require_http_methods(['GET'])
def api_stock(request):
    """GET /api/v1/stock/ — Ringkasan stok (nama, barcode, stok, status)"""
    cabang = _authenticate(request)
    if not cabang:
        return _err('Unauthorized', 401)

    from stock.models import Barang
    items = list(Barang.objects.filter(cabang=cabang).order_by('nama').values(
        'id', 'barcode', 'nama', 'satuan', 'stok', 'harga_ecer'
    ))
    for i in items:
        s = i['stok']
        i['status'] = 'habis' if s == 0 else ('rendah' if s < 5 else 'tersedia')

    return _ok(items, total=len(items))


@csrf_exempt
@require_http_methods(['GET'])
def api_info(request):
    """GET /api/v1/info/ — Info toko + paket aktif"""
    cabang = _authenticate(request)
    if not cabang:
        return _err('Unauthorized', 401)

    info = {
        'nama_toko': cabang.nama_toko,
        'nama_cabang': cabang.nama_cabang,
        'kode_toko': cabang.prefix,
        'email': cabang.email,
        'paket': cabang.paket.nama if cabang.paket else ('Korporasi' if cabang.owner_id else 'Paket Dasar'),
        'kuota_transaksi': cabang.kuota_transaksi,
        'is_email_verified': cabang.is_email_verified,
    }
    return _ok(info)


# ── Webhook registration ──────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET', 'POST', 'DELETE'])
def api_webhooks(request):
    """
    GET  /api/v1/webhooks/  — List webhook endpoints
    POST /api/v1/webhooks/  — Daftarkan webhook baru
    DELETE /api/v1/webhooks/?id=<id> — Hapus webhook
    """
    cabang = _authenticate(request)
    if not cabang:
        return _err('Unauthorized', 401)

    from .models import WebhookEndpoint

    if request.method == 'GET':
        hooks = list(WebhookEndpoint.objects.filter(cabang=cabang, is_active=True).values(
            'id', 'url', 'event', 'created_at'
        ))
        for h in hooks:
            if h['created_at']:
                h['created_at'] = h['created_at'].isoformat()
        return _ok(hooks)

    if request.method == 'POST':
        try:
            body = json.loads(request.body)
        except Exception:
            return _err("Body harus JSON: {url, event}")
        url   = body.get('url', '').strip()
        event = body.get('event', '').strip()
        valid_events = [e[0] for e in WebhookEndpoint.EVENT_CHOICES]
        if not url or not event:
            return _err("Wajib: url, event")
        if event not in valid_events:
            return _err(f"Event tidak valid. Pilihan: {', '.join(valid_events)}")
        hook = WebhookEndpoint.objects.create(cabang=cabang, url=url, event=event)
        return _ok({'id': hook.id, 'url': hook.url, 'event': hook.event, 'secret': hook.secret}, status=201)

    if request.method == 'DELETE':
        hook_id = request.GET.get('id')
        try:
            WebhookEndpoint.objects.filter(id=hook_id, cabang=cabang).delete()
            return _ok({'deleted': True})
        except Exception as e:
            return _err(str(e))

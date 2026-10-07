import datetime
import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from cms.views import addLog
from payment.models import AddonConfig, TokoAddon
from pos.models import Penjualan, PenjualanDetail
from pos.views import cek_expired_kuota, _korporasi_aktif
from stock.models import Barang, Cabang

from .permissions import IsKasirAktif
from .serializers import (BarangSerializer, CheckoutSerializer, LoginSerializer,
                          serialize_sale)

log = logging.getLogger(__name__)


def ok(data=None, http=status.HTTP_200_OK):
    return Response({'success': True, 'data': data}, status=http)


def fail(msg, http=status.HTTP_400_BAD_REQUEST, detail=None):
    return Response({'success': False, 'error': msg, 'detail': detail}, status=http)


def _cabang(request):
    return request.user.userprofile.cabang


def _can_tempo(cabang):
    return not (cabang.paket is None and cabang.owner_id is None)


def _toko_info(cabang):
    nota_config = {}
    addon = TokoAddon.get_for_cabang(cabang, TokoAddon.ADDON_NOTA)
    if addon:
        cfg = AddonConfig.objects.filter(cabang=cabang, addon_type=TokoAddon.ADDON_NOTA).first()
        if cfg:
            nota_config = cfg.config
    return {
        'nama': cabang.nama_toko,
        'alamat': cabang.alamat_toko,
        'telpon': cabang.telpon,
        'watermark': cabang.paket is None and cabang.owner_id is None,
        'nota_custom': bool(addon),
        'nota_config': nota_config,
    }


def _user_info(user):
    cabang = user.userprofile.cabang
    nama = user.userprofile.nama_lengkap.strip()
    return {
        'username': user.username,
        'nama_lengkap': nama,
        'kasir_nama': nama.split()[0] if nama else user.username,
        'can_edit_harga': user.is_superuser,
        'can_tempo': _can_tempo(cabang),
        'toko': _toko_info(cabang),
    }


def _tokens(user):
    r = RefreshToken.for_user(user)
    return {'access': str(r.access_token), 'refresh': str(r)}


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        username = s.validated_data['username'].strip().lower()
        password = s.validated_data['password']

        user = authenticate(username=username, password=password)
        if user is None:
            # sama seperti web: login dengan email cabang → kasir utama {prefix}1
            cabang = Cabang.objects.filter(email=username).first()
            if cabang and cabang.prefix:
                user = authenticate(username=f'{cabang.prefix}1', password=password)

        # Pesan seragam agar tidak membocorkan keberadaan akun.
        if user is None:
            addLog('', '', 'login-mobile', f'login mobile gagal untuk user {username}')
            return fail('Username atau password tidak sesuai.', status.HTTP_401_UNAUTHORIZED)

        profile = getattr(user, 'userprofile', None)
        if user.is_staff or profile is None:
            return fail('Akun ini tidak dapat digunakan pada aplikasi kasir.', status.HTTP_403_FORBIDDEN)
        if not profile.is_active or not profile.cabang.is_active:
            addLog(user, profile.cabang, 'login-mobile', 'pengguna dinonaktifkan, tidak bisa login.')
            return fail('Pengguna dinonaktifkan. Hubungi pemilik toko.', status.HTTP_403_FORBIDDEN)

        addLog(user, profile.cabang, 'login-mobile', 'login mobile berhasil')
        return ok({**_tokens(user), 'user': _user_info(user)})


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        s = TokenRefreshSerializer(data=request.data)
        try:
            s.is_valid(raise_exception=True)
        except TokenError:
            return fail('Sesi berakhir, silakan login kembali.', status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return fail('Sesi berakhir, silakan login kembali.', status.HTTP_401_UNAUTHORIZED)
        return ok({'access': s.validated_data['access'],
                   'refresh': s.validated_data.get('refresh')})


class LogoutView(APIView):
    def post(self, request):
        token = request.data.get('refresh')
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        try:
            addLog(request.user, request.user.userprofile.cabang, 'logout-mobile', 'logout mobile berhasil')
        except Exception:
            pass
        return ok()


class MeView(APIView):
    permission_classes = [IsKasirAktif]

    def get(self, request):
        cabang = _cabang(request)
        return ok({**_user_info(request.user),
                   'bisa_transaksi': bool(cek_expired_kuota(cabang.id))})


# ── Produk ───────────────────────────────────────────────────────────────────

class ProductListView(APIView):
    permission_classes = [IsKasirAktif]

    def get(self, request):
        qs = Barang.objects.filter(cabang=_cabang(request)).order_by('nama')
        if request.GET.get('stok_ada', '1') != '0':
            qs = qs.filter(stok__gt=0)
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nama__icontains=q) | Q(barcode__icontains=q))
        try:
            per_page = max(1, min(int(request.GET.get('per_page', 50)), 100))
            page = max(1, int(request.GET.get('page', 1)))
        except ValueError:
            return fail('Parameter page/per_page tidak valid.')
        total = qs.count()
        rows = qs[(page - 1) * per_page: page * per_page]
        return ok({'count': total, 'page': page, 'per_page': per_page,
                   'results': BarangSerializer(rows, many=True).data})


class ProductByBarcodeView(APIView):
    permission_classes = [IsKasirAktif]

    def get(self, request, kode):
        barang = Barang.objects.filter(cabang=_cabang(request), barcode=kode).first()
        if not barang:
            return fail('Barang dengan kode tersebut belum ada.', status.HTTP_404_NOT_FOUND)
        return ok(BarangSerializer(barang).data)


# ── Penjualan ────────────────────────────────────────────────────────────────

class CheckoutView(APIView):
    """Bayar satu keranjang secara atomik. Stok, harga, kuota & no. nota dihitung server."""
    permission_classes = [IsKasirAktif]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'checkout'

    def post(self, request):
        s = CheckoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user = request.user
        cabang_id = _cabang(request).id

        # Idempotensi: retry dengan nota yang sama mengembalikan hasil sebelumnya.
        existing = Penjualan.objects.filter(nota=d['nota']).first()
        if existing:
            if existing.user_id == user.id and existing.cabang_id == cabang_id and existing.is_paid:
                return ok(self._receipt(existing, cabang_id), status.HTTP_200_OK)
            return fail('Nomor nota sudah dipakai.', status.HTTP_409_CONFLICT)

        if not cek_expired_kuota(cabang_id):
            return fail('Kuota transaksi habis atau lisensi toko kedaluwarsa.', status.HTTP_403_FORBIDDEN)

        items = d['items']
        if any('harga' in i for i in items) and not user.is_superuser:
            return fail('Hanya admin yang boleh mengubah harga.', status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            cabang = Cabang.objects.select_for_update().get(id=cabang_id)
            if d['metode'] == 2 and not _can_tempo(cabang):
                return fail('Pembayaran tempo tidak tersedia untuk paket gratis.', status.HTTP_403_FORBIDDEN)

            barang_map = {
                b.id: b for b in Barang.objects.select_for_update()
                .filter(cabang=cabang, id__in=[i['barang_id'] for i in items])
            }
            missing = [i['barang_id'] for i in items if i['barang_id'] not in barang_map]
            if missing:
                return fail('Ada barang yang tidak ditemukan.', status.HTTP_400_BAD_REQUEST, {'barang_id': missing})
            kurang = [{'barang_id': i['barang_id'], 'nama': barang_map[i['barang_id']].nama,
                       'stok': barang_map[i['barang_id']].stok}
                      for i in items if barang_map[i['barang_id']].stok < i['jumlah']]
            if kurang:
                return fail('Stok tidak mencukupi.', status.HTTP_409_CONFLICT, {'stok_kurang': kurang})

            penjualan = Penjualan.objects.create(nota=d['nota'], cabang=cabang, user=user)
            for i in items:
                barang = barang_map[i['barang_id']]
                detail = PenjualanDetail(penjualan=penjualan, barang=barang, jumlah=i['jumlah'])
                if 'harga' in i:
                    detail.is_open = True
                    detail.harga = i['harga']
                detail.save()
                barang.stok -= i['jumlah']
                barang.jumlah_dibeli += i['jumlah']
                barang.save(update_fields=['stok', 'jumlah_dibeli'])

            penjualan.refresh_from_db()
            penjualan.is_paid = True
            penjualan.metode = d['metode']
            penjualan.customer = d['pembeli']
            penjualan.no_nota = str(cabang.no_nota).zfill(5)
            if d['metode'] == 2:
                penjualan.tgl_bayar = None
                penjualan.jatuh_tempo = d['jatuh_tempo']
                penjualan.is_tempo_lunas = False
            else:
                penjualan.tgl_bayar = datetime.datetime.now()
            penjualan.save()

            cabang.no_nota += 1
            if cabang.owner_id and _korporasi_aktif(cabang):
                owner = cabang.owner
                if owner.kuota_transaksi_pool > 0:
                    owner.kuota_transaksi_pool -= 1
                    owner.save()
            elif cabang.owner_id:
                if cabang.kuota_transaksi > 0:
                    cabang.kuota_transaksi -= 1
            else:
                cabang.kuota_transaksi -= 1
            cabang.save()

            addLog(user, cabang, 'pembayaran',
                   f"{'Pembayaran Tempo' if d['metode'] == 2 else 'Pembayaran'} (mobile) no. transaksi: {penjualan.nota}")

        return ok(self._receipt(penjualan, cabang_id), status.HTTP_201_CREATED)

    @staticmethod
    def _receipt(penjualan, cabang_id):
        cabang = Cabang.objects.get(id=cabang_id)
        return {**serialize_sale(penjualan), 'toko': _toko_info(cabang),
                'kasir': _user_info(penjualan.user)['kasir_nama'],
                'kasir_username': penjualan.user.username}


def _own_sales(request):
    return Penjualan.objects.filter(cabang=_cabang(request), user=request.user, is_paid=True)


class SaleListView(APIView):
    permission_classes = [IsKasirAktif]

    def get(self, request):
        qs = _own_sales(request).order_by('-created_at')
        tgl = request.GET.get('tanggal')
        if tgl:
            try:
                dt = datetime.date.fromisoformat(tgl)
            except ValueError:
                return fail('Format tanggal: YYYY-MM-DD.')
            qs = qs.filter(Q(tgl_bayar__date=dt) | Q(tgl_bayar__isnull=True, created_at__date=dt))
        try:
            per_page = max(1, min(int(request.GET.get('per_page', 30)), 100))
            page = max(1, int(request.GET.get('page', 1)))
        except ValueError:
            return fail('Parameter page/per_page tidak valid.')
        total = qs.count()
        rows = qs[(page - 1) * per_page: page * per_page]
        return ok({'count': total, 'page': page, 'per_page': per_page,
                   'results': [serialize_sale(p, with_items=False) for p in rows]})


class SaleDetailView(APIView):
    permission_classes = [IsKasirAktif]

    def get(self, request, nota):
        p = get_object_or_404(_own_sales(request), nota=nota)
        return ok(CheckoutView._receipt(p, p.cabang_id))


class SaleReprintView(APIView):
    permission_classes = [IsKasirAktif]

    def post(self, request, nota):
        p = get_object_or_404(_own_sales(request).filter(is_void=False), nota=nota)
        p.reprint_nota += 1
        p.save(update_fields=['reprint_nota'])
        return ok(CheckoutView._receipt(p, p.cabang_id))

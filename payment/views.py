import datetime
import hashlib
import json
import uuid as _uuid_mod

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password as _mkpw
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render

import midtransclient

from pos.models import DetailWalet, Penjualan
from posmimail import posmiMail
from promo.models import Promo, PromoUsed
from promo.views import cekKodeToko, cekKodeVoucher
from stock.models import Cabang, DaftarPaket, LogTransaksi, UserProfile, prefixGenerator

from .models import GaransiRefund, PendingPayment, PermintaanKonsultasi, TokoAddon, TransaksiPembelian

# ── Konstanta ─────────────────────────────────────────────────────────────────
REFUND_AUTO_LIMIT_TRANSAKSI = 50
PAKET_GRATIS_KUOTA_BULANAN  = 75

DAY_MAP = {
    'bulanan': 30, 'tigabulanan': 90, 'enambulanan': 180,
    'tahunan': 365, 'duatahunan': 730,
}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _buat_order_id(prefix):
    return f"{prefix}-{_uuid_mod.uuid4().hex[:10].upper()}"


def _sesuaikan_kasir_downgrade(cabang, max_kasir):
    """Nonaktifkan kasir yang melebihi kuota paket baru. 0 = unlimited."""
    if max_kasir == 0:
        return []
    kasir_qs = (
        UserProfile.objects
        .filter(cabang=cabang, user__is_superuser=False)
        .select_related('user')
        .order_by('user__username')
    )
    dinonaktifkan = []
    for idx, profile in enumerate(kasir_qs):
        if idx < max_kasir:
            if not profile.is_active:
                profile.is_active = True
                profile.save(update_fields=['is_active'])
        else:
            if profile.is_active:
                profile.is_active = False
                profile.save(update_fields=['is_active'])
                dinonaktifkan.append(profile.user.username)
    return dinonaktifkan


def getAdmin(kode_toko):
    try:
        return UserProfile.objects.get(user__username=f"{kode_toko}1").nama_lengkap
    except Exception:
        return ""


def get_jumlah_bulan_paket(pkt):
    return {1: 3, 2: 6, 3: 12, 4: 24}.get(pkt, 1)


def prosesPayment(noTransaksi, jumlah, nama_pembeli='', email_pembeli='', finish_url=''):
    params = {
        'transaction_details': {
            'order_id': noTransaksi,
            'gross_amount': jumlah,
        },
        'credit_card': {'secure': True},
    }
    if nama_pembeli or email_pembeli:
        params['customer_details'] = {'first_name': nama_pembeli, 'email': email_pembeli}
    if finish_url:
        params['callbacks'] = {'finish': finish_url}
    snap = midtransclient.Snap(
        is_production=settings.MIDTRANS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER,
        client_key=settings.MIDTRANS_CLIENT,
    )
    return snap.create_transaction(params)['redirect_url']


def _proses_pending_payment(pending):
    """Eksekusi transaksi setelah Midtrans mengonfirmasi pembayaran."""
    d = pending.data

    # ── REGISTRASI ────────────────────────────────────────────────────────────
    if pending.tipe == PendingPayment.TIPE_REGISTRASI:
        tipe         = d['tipe']
        pkt          = d['pkt']
        kode_toko    = d['kode_toko']
        nama_toko    = d['nama_toko']
        email_toko   = d['email_toko']
        pemilik_toko = d['pemilik_toko']
        referensi    = d.get('referensi', '')
        voucher_kode = d.get('voucher', '')
        lisensi_days = d.get('lisensi_days', 0)
        jumlah_transaksi = d.get('jumlah_transaksi', PAKET_GRATIS_KUOTA_BULANAN)

        if Cabang.objects.filter(email=email_toko).exists():
            return

        daftarpaket = None
        if tipe == 'sm':
            daftarpaket = DaftarPaket.objects.filter(nama='Bisnis Kecil').first()
        elif tipe == 'med':
            daftarpaket = DaftarPaket.objects.filter(nama='Bisnis Medium').first()

        lisensi_expired = (datetime.datetime.now() + datetime.timedelta(days=lisensi_days)) if lisensi_days else None
        lisensi_grace   = (lisensi_expired + datetime.timedelta(days=7)) if lisensi_expired else None

        cabang = Cabang(
            paket=daftarpaket, nama_toko=nama_toko, nama_cabang=d['nama_cabang'],
            alamat_toko=d['alamat_toko'], telpon=d['telpon'], email=email_toko,
            prefix=kode_toko, lisensi_expired=lisensi_expired, lisensi_grace=lisensi_grace,
            kuota_transaksi=jumlah_transaksi, kode_referal=referensi or None, no_nota=1,
        )
        cabang.save()

        if tipe != 'tr' and pending.harga > 0:
            GaransiRefund.objects.create(
                cabang=cabang, paket=daftarpaket,
                jumlah_pembayaran=pending.harga,
                jumlah_bulan=get_jumlah_bulan_paket(pkt),
                tanggal_aktivasi=datetime.datetime.now(),
                batas_pengajuan=datetime.datetime.now() + datetime.timedelta(days=30),
            )

        if voucher_kode:
            try:
                promo = Promo.objects.get(kode=voucher_kode)
                PromoUsed.objects.create(promo=promo, cabang=cabang)
                promo.kuota -= 1
                promo.save()
            except Exception:
                pass

        if referensi:
            try:
                ref_cabang = Cabang.objects.get(prefix=referensi)
                bonus = int(pending.harga * 5 / 100)
                ref_cabang.wallet += bonus
                ref_cabang.save()
                DetailWalet.objects.create(
                    cabang=ref_cabang, cabang_referensi=cabang,
                    jumlah=bonus, keterangan='registrasi toko',
                )
            except Exception:
                pass

        user = User(username=f"{kode_toko}1", email=email_toko,
                    first_name=pemilik_toko, is_active=True, is_superuser=True)
        user.password = d['pw_hash']
        user.save()
        UserProfile.objects.create(user=user, cabang=cabang, nama_lengkap=pemilik_toko, is_active=True)

        posmiMail(
            "Terima Kasih Sudah Menggunakan POSMI",
            f"Halo Sobat {pemilik_toko}!\n\nAkun POSMI toko {nama_toko} sudah aktif.\n"
            f"Username: {kode_toko}1\nKode Toko: {kode_toko}\n\n"
            f"Login: https://posmi.pythonanywhere.com/login/",
            address=email_toko,
        )

    # ── UPGRADE / PERPANJANGAN ────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_UPGRADE:
        try:
            cabang = Cabang.objects.get(prefix=d['kode_toko'])
        except Cabang.DoesNotExist:
            return
        paket            = DaftarPaket.objects.get(paket=d['paket_id'])
        paket_sebelumnya = cabang.paket
        day              = d['day']

        if cabang.lisensi_expired and cabang.lisensi_expired > datetime.datetime.now():
            tanggal_expired = cabang.lisensi_expired + datetime.timedelta(days=day)
        else:
            tanggal_expired = datetime.datetime.now() + datetime.timedelta(days=day)

        wallet_dipakai = int(d.get('wallet_dipakai', 0))
        cabang.lisensi_expired = tanggal_expired
        cabang.lisensi_grace   = tanggal_expired + datetime.timedelta(days=7)
        cabang.kuota_transaksi = (
            paket.max_transaksi if paket_sebelumnya is None
            else cabang.kuota_transaksi + paket.max_transaksi
        )
        cabang.paket = paket
        if wallet_dipakai > 0:
            cabang.wallet = max(0, cabang.wallet - wallet_dipakai)
        cabang.save()

        if wallet_dipakai > 0:
            DetailWalet.objects.create(
                cabang=cabang,
                keterangan=f'potongan wallet upgrade paket {paket.nama}',
                jumlah=wallet_dipakai,
            )

        if paket_sebelumnya is None and not GaransiRefund.objects.filter(cabang=cabang).exists():
            GaransiRefund.objects.create(
                cabang=cabang, paket=paket,
                jumlah_pembayaran=pending.harga, jumlah_bulan=1,
                tanggal_aktivasi=datetime.datetime.now(),
                batas_pengajuan=datetime.datetime.now() + datetime.timedelta(days=30),
            )

        _sesuaikan_kasir_downgrade(cabang, paket.max_user_login)

    # ── TAMBAH KUOTA ──────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_KUOTA:
        try:
            cabang = Cabang.objects.get(prefix=d['kode_toko'])
        except Cabang.DoesNotExist:
            return
        jumlah_kuota   = int(d['jumlah_kuota'])
        wallet_dipakai = int(d.get('wallet_dipakai', 0))

        cabang.kuota_transaksi += jumlah_kuota
        if wallet_dipakai > 0:
            cabang.wallet = max(0, cabang.wallet - wallet_dipakai)
        cabang.save()

        if wallet_dipakai > 0:
            DetailWalet.objects.create(
                cabang=cabang,
                keterangan=f'potongan wallet tambah kuota {jumlah_kuota}',
                jumlah=wallet_dipakai,
            )

        if d.get('voucher'):
            try:
                promo = Promo.objects.get(kode=d['voucher'])
                PromoUsed.objects.create(promo=promo, cabang=cabang)
                promo.kuota -= 1
                promo.save()
            except Exception:
                pass

        if d.get('referensi'):
            try:
                ref = Cabang.objects.get(prefix=d['referensi'])
                bonus = int(pending.harga * 5 / 100)
                ref.wallet += bonus
                ref.save()
                DetailWalet.objects.create(
                    cabang=ref, cabang_referensi=cabang,
                    jumlah=bonus, keterangan='tambah kuota transaksi',
                )
            except Exception:
                pass

        try:
            user_adm = User.objects.get(username=f"{cabang.prefix}1")
            posmiMail(
                "Kuota Transaksi Berhasil Ditambahkan",
                f"Halo {user_adm.first_name},\n\nKuota {jumlah_kuota:,} transaksi telah ditambahkan.\n"
                f"Total kuota saat ini: {cabang.kuota_transaksi:,}",
                address=cabang.email,
            )
        except Exception:
            pass

    # ── ADD-ON ────────────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_ADDON:
        addon_type = d['addon_type']
        if d.get('kode_toko'):
            try:
                cabang = Cabang.objects.get(prefix=d['kode_toko'])
                addon  = TokoAddon.objects.filter(cabang=cabang, addon_type=addon_type).first()
                if addon:
                    addon.status       = TokoAddon.STATUS_AKTIF
                    addon.activated_at = datetime.datetime.now()
                    addon.expired_at   = cabang.lisensi_expired
                    addon.harga_dibayar = pending.harga
                    addon.save()
            except Exception:
                pass
        elif d.get('owner_id'):
            try:
                from owner.models import Owner
                owner = Owner.objects.get(pk=d['owner_id'])
                addon = TokoAddon.objects.filter(owner=owner, addon_type=addon_type).first()
                if addon:
                    addon.status       = TokoAddon.STATUS_AKTIF
                    addon.activated_at = datetime.datetime.now()
                    addon.expired_at   = owner.lisensi_expired
                    addon.harga_dibayar = pending.harga
                    addon.save()
            except Exception:
                pass

    # ── OWNER UPGRADE ─────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_OWNER:
        try:
            from owner.models import Owner
            owner = Owner.objects.get(pk=d['owner_id'])
            day   = d['day']
            now   = datetime.datetime.now()
            owner.lisensi_expired = (
                owner.lisensi_expired + datetime.timedelta(days=day)
                if owner.lisensi_expired and owner.lisensi_expired > now
                else now + datetime.timedelta(days=day)
            )
            owner.lisensi_grace = owner.lisensi_expired + datetime.timedelta(days=7)
            owner.save()
        except Exception:
            pass

    # ── Catat TransaksiPembelian ──────────────────────────────────────────────
    try:
        keterangan_map = {
            PendingPayment.TIPE_REGISTRASI: f"Registrasi toko {d.get('nama_toko', '')}",
            PendingPayment.TIPE_UPGRADE:    f"Upgrade/Perpanjangan paket — {d.get('metode', '')}",
            PendingPayment.TIPE_KUOTA:      f"Tambah kuota {d.get('jumlah_kuota', '')} transaksi",
            PendingPayment.TIPE_ADDON:      f"Aktivasi add-on {d.get('addon_type', '')}",
            PendingPayment.TIPE_OWNER:      f"Upgrade korporasi — {d.get('metode', '')}",
        }
        cabang_obj = Cabang.objects.filter(prefix=d['kode_toko']).first() if d.get('kode_toko') else None
        owner_obj  = None
        if d.get('owner_id'):
            try:
                from owner.models import Owner as _Owner
                owner_obj = _Owner.objects.get(pk=d['owner_id'])
            except Exception:
                pass
        TransaksiPembelian.objects.create(
            cabang=cabang_obj, owner=owner_obj,
            order_id=pending.order_id, tipe=pending.tipe,
            keterangan=keterangan_map.get(pending.tipe, ''),
            harga=pending.harga,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  ADD-ON VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def bayarAddon(request):
    """Form modal add-on → buat PendingPayment → redirect ke Midtrans."""
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = '/'

    if request.method != 'POST':
        return HttpResponseRedirect(asal)

    addon_type  = request.POST.get('addon_type', '').strip()
    kode_toko   = request.POST.get('kode_toko', '').strip().lower()
    email_owner = request.POST.get('email_owner', '').strip().lower()

    valid_types = [c[0] for c in TokoAddon.ADDON_CHOICES]
    if addon_type not in valid_types:
        messages.add_message(request, messages.SUCCESS, "Jenis add-on tidak valid.")
        return HttpResponseRedirect(asal)

    harga = TokoAddon.HARGA.get(addon_type, 0)

    # ── Individual ────────────────────────────────────────────────────────────
    if kode_toko:
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
        except Cabang.DoesNotExist:
            messages.add_message(request, messages.SUCCESS, f"Kode toko '{kode_toko}' tidak ditemukan.")
            return HttpResponseRedirect(asal)

        if cabang.paket is None and cabang.owner_id is None:
            messages.add_message(request, messages.SUCCESS,
                "Paket Gratis tidak dapat menggunakan add-on. Upgrade paket terlebih dahulu.")
            return HttpResponseRedirect(asal)

        if cabang.owner_id:
            messages.add_message(request, messages.SUCCESS,
                "Toko Korporasi: gunakan tab Korporasi dan masukkan email pemilik.")
            return HttpResponseRedirect(asal)

        TokoAddon.objects.get_or_create(
            cabang=cabang, addon_type=addon_type,
            defaults={'expired_at': cabang.lisensi_expired, 'harga_dibayar': harga,
                      'status': TokoAddon.STATUS_NONAKTIF},
        )
        order_id   = _buat_order_id('ADN')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_ADDON,
            data={'addon_type': addon_type, 'kode_toko': kode_toko},
            harga=harga,
        )
        try:
            redirect_url = prosesPayment(order_id, harga,
                                         nama_pembeli=cabang.nama_toko,
                                         email_pembeli=cabang.email or '',
                                         finish_url=finish_url)
            return HttpResponseRedirect(redirect_url)
        except Exception as ex:
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                "Gagal membuat transaksi pembayaran. Silakan coba beberapa saat lagi.")
            return HttpResponseRedirect(asal)

    # ── Korporasi ─────────────────────────────────────────────────────────────
    if email_owner:
        try:
            owner = User.objects.get(email__iexact=email_owner).owner_profile
        except Exception:
            messages.add_message(request, messages.SUCCESS,
                f"Email '{email_owner}' tidak ditemukan sebagai akun Korporasi.")
            return HttpResponseRedirect(asal)

        if not owner.is_active:
            messages.add_message(request, messages.SUCCESS,
                "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu.")
            return HttpResponseRedirect(asal)

        TokoAddon.objects.get_or_create(
            owner=owner, addon_type=addon_type,
            defaults={'expired_at': owner.lisensi_expired, 'harga_dibayar': harga,
                      'status': TokoAddon.STATUS_NONAKTIF},
        )
        order_id   = _buat_order_id('ADN')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_ADDON,
            data={'addon_type': addon_type, 'owner_id': str(owner.pk)},
            harga=harga,
        )
        try:
            redirect_url = prosesPayment(order_id, harga,
                                         nama_pembeli=owner.nama,
                                         email_pembeli=email_owner,
                                         finish_url=finish_url)
            return HttpResponseRedirect(redirect_url)
        except Exception as ex:
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                "Gagal membuat transaksi pembayaran. Silakan coba beberapa saat lagi.")
            return HttpResponseRedirect(asal)

    messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email owner Korporasi.")
    return HttpResponseRedirect(asal)


def requestAddon(request):
    """Permintaan aktivasi add-on (termasuk trial bundle) dari landing page."""
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = "/"

    if request.method != 'POST':
        return HttpResponseRedirect(asal)

    addon_type  = request.POST.get('addon_type', '').strip()
    kode_toko   = request.POST.get('kode_toko', '').strip().lower()
    email_owner = request.POST.get('email_owner', '').strip().lower()

    # ── Trial Bundle ──────────────────────────────────────────────────────────
    if addon_type == 'trial_bundle':
        target_cabang = None
        target_owner  = None

        if kode_toko:
            try:
                target_cabang = Cabang.objects.get(prefix=kode_toko)
            except Cabang.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, f"Kode toko '{kode_toko}' tidak ditemukan.")
                return HttpResponseRedirect(asal)
            if target_cabang.paket is None and target_cabang.owner_id is None:
                messages.add_message(request, messages.SUCCESS,
                    "Trial hanya untuk paket berbayar (Bisnis Kecil/Medium/Korporasi).")
                return HttpResponseRedirect(asal)
            if target_cabang.owner_id:
                target_owner  = target_cabang.owner
                target_cabang = None
        elif email_owner:
            try:
                target_owner = User.objects.get(email__iexact=email_owner).owner_profile
            except Exception:
                messages.add_message(request, messages.SUCCESS, f"Email '{email_owner}' tidak ditemukan.")
                return HttpResponseRedirect(asal)

        if not target_cabang and not target_owner:
            messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email Korporasi.")
            return HttpResponseRedirect(asal)

        trial_end = datetime.datetime.now() + datetime.timedelta(days=3)
        all_types = [TokoAddon.ADDON_BARCODE, TokoAddon.ADDON_NOTA, TokoAddon.ADDON_AKUNTING]
        for atype in all_types:
            kwargs = {'cabang': target_cabang} if target_cabang else {'owner': target_owner}
            kwargs['addon_type'] = atype
            if not TokoAddon.objects.filter(**kwargs).exists():
                TokoAddon.objects.create(
                    **{k: v for k, v in kwargs.items()},
                    status=TokoAddon.STATUS_NONAKTIF,
                    expired_at=trial_end,
                    harga_dibayar=0,
                    catatan_admin='trial_3hari',
                )

        nama = target_cabang.nama_toko if target_cabang else target_owner.nama
        posmiMail(
            "REQUEST TRIAL BUNDLE 3 HARI",
            f"{'Toko' if target_cabang else 'Owner Korporasi'}: {nama}\n"
            f"Trial bundle: {', '.join(all_types)}\nBerlaku 3 hari.\n\nAktifkan di Django Admin.",
            address="adhy.chandra@live.co.uk",
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan trial 3 hari untuk {nama} berhasil dikirim.")
        return HttpResponseRedirect(asal)

    valid_types = [c[0] for c in TokoAddon.ADDON_CHOICES]
    if addon_type not in valid_types:
        messages.add_message(request, messages.SUCCESS, "Jenis add-on tidak valid.")
        return HttpResponseRedirect(asal)

    # ── Individual ────────────────────────────────────────────────────────────
    if kode_toko:
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
        except Cabang.DoesNotExist:
            messages.add_message(request, messages.SUCCESS, f"Kode toko '{kode_toko}' tidak ditemukan.")
            return HttpResponseRedirect(asal)

        if cabang.paket is None and cabang.owner_id is None:
            messages.add_message(request, messages.SUCCESS,
                "Paket Gratis tidak dapat menggunakan add-on ini. Upgrade terlebih dahulu.")
            return HttpResponseRedirect(asal)

        if cabang.owner_id:
            messages.add_message(request, messages.SUCCESS,
                "Toko Korporasi: gunakan email pemilik untuk mengaktifkan add-on.")
            return HttpResponseRedirect(asal)

        harga = TokoAddon.HARGA.get(addon_type, 0)
        addon, created = TokoAddon.objects.get_or_create(
            cabang=cabang, addon_type=addon_type,
            defaults={'expired_at': cabang.lisensi_expired, 'harga_dibayar': harga,
                      'status': TokoAddon.STATUS_NONAKTIF},
        )
        if not created:
            addon.expired_at = cabang.lisensi_expired
            addon.save(update_fields=['expired_at', 'updated_at'])

        posmiMail(
            f"REQUEST ADD-ON: {addon.get_addon_type_display()}",
            f"Toko: {cabang.nama_toko} ({kode_toko})\nAdd-on: {addon.get_addon_type_display()}\n"
            f"Harga: Rp {harga:,}\nAktifkan via Django Admin.",
            address="adhy.chandra@live.co.uk",
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan add-on '{addon.get_addon_type_display()}' untuk toko {cabang.nama_toko} "
            f"berhasil dikirim.")
        return HttpResponseRedirect(asal)

    # ── Korporasi ─────────────────────────────────────────────────────────────
    if email_owner:
        try:
            owner = User.objects.get(email__iexact=email_owner).owner_profile
        except Exception:
            messages.add_message(request, messages.SUCCESS,
                f"Email pemilik Korporasi '{email_owner}' tidak ditemukan.")
            return HttpResponseRedirect(asal)

        if not owner.is_active:
            messages.add_message(request, messages.SUCCESS,
                "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu.")
            return HttpResponseRedirect(asal)

        harga = TokoAddon.HARGA.get(addon_type, 0)
        addon, created = TokoAddon.objects.get_or_create(
            owner=owner, addon_type=addon_type,
            defaults={'expired_at': owner.lisensi_expired, 'harga_dibayar': harga,
                      'status': TokoAddon.STATUS_NONAKTIF},
        )
        if not created:
            addon.expired_at = owner.lisensi_expired
            addon.save(update_fields=['expired_at', 'updated_at'])

        posmiMail(
            f"REQUEST ADD-ON KORPORASI: {addon.get_addon_type_display()}",
            f"Owner: {owner.nama} ({email_owner})\nAdd-on: {addon.get_addon_type_display()}\n"
            f"Harga: Rp {harga:,}\nAktifkan via Django Admin.",
            address="adhy.chandra@live.co.uk",
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan add-on '{addon.get_addon_type_display()}' untuk Korporasi {owner.nama} "
            f"berhasil dikirim.")
        return HttpResponseRedirect(asal)

    messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email owner Korporasi.")
    return HttpResponseRedirect(asal)


def addonStatus(request):
    """Validasi kode toko / email korporasi + cek status add-on (untuk modal landing page)."""
    kode       = request.GET.get('kode', '').strip().lower()
    email      = request.GET.get('email', '').strip().lower()
    addon_type = request.GET.get('addon_type', '').strip()

    if kode:
        try:
            cabang = Cabang.objects.get(prefix=kode)
        except Cabang.DoesNotExist:
            return JsonResponse({'ok': False, 'pesan': f"Kode toko '{kode}' tidak ditemukan."})

        if cabang.paket is None and cabang.owner_id is None:
            return JsonResponse({'ok': False,
                'pesan': f"Toko '{cabang.nama_toko}' masih Paket Gratis. Upgrade untuk menggunakan add-on."})

        if cabang.owner_id:
            return JsonResponse({'ok': False,
                'pesan': "Toko Korporasi: gunakan tab 'Korporasi' dan masukkan email pemilik."})

        if addon_type:
            existing = TokoAddon.objects.filter(cabang=cabang, addon_type=addon_type).first()
            if existing and existing.is_active:
                exp = existing.expired_at.strftime('%d/%m/%Y') if existing.expired_at else '-'
                return JsonResponse({
                    'ok': True, 'sudah_aktif': True, 'toko_nama': cabang.nama_toko,
                    'expired_at': exp,
                    'pesan': f"Toko '{cabang.nama_toko}' sudah berlangganan hingga {exp}. Klik untuk memperpanjang.",
                })

        return JsonResponse({'ok': True, 'sudah_aktif': False, 'toko_nama': cabang.nama_toko,
                             'pesan': f"Toko '{cabang.nama_toko}' ditemukan. Paket: {cabang.paket.nama}."})

    if email:
        try:
            owner = User.objects.get(email__iexact=email).owner_profile
        except Exception:
            return JsonResponse({'ok': False,
                'pesan': f"Email '{email}' tidak ditemukan sebagai akun Korporasi."})

        if not owner.is_active:
            return JsonResponse({'ok': False,
                'pesan': "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu."})

        if addon_type:
            existing = TokoAddon.objects.filter(owner=owner, addon_type=addon_type).first()
            if existing and existing.is_active:
                exp = existing.expired_at.strftime('%d/%m/%Y') if existing.expired_at else '-'
                return JsonResponse({
                    'ok': True, 'sudah_aktif': True, 'toko_nama': owner.nama,
                    'expired_at': exp,
                    'pesan': f"Akun Korporasi '{owner.nama}' sudah berlangganan hingga {exp}.",
                })

        return JsonResponse({'ok': True, 'sudah_aktif': False, 'toko_nama': owner.nama,
                             'pesan': f"Akun Korporasi '{owner.nama}' ditemukan."})

    return JsonResponse({'ok': False, 'pesan': ''})


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRASI & PAYMENT REQUEST
# ══════════════════════════════════════════════════════════════════════════════

def paymentRequest(request):
    """Render halaman registrasi berdasarkan pilihan paket dari landing page."""
    if request.method != "POST":
        return HttpResponseRedirect('/')

    paket = ""
    harga = None
    kode_toko   = prefixGenerator()
    jenis_paket = ""
    tipe        = None
    pkt         = None
    daftarpaket = None

    now = datetime.datetime.now()

    if 'bisnis_kecil' in request.POST:
        tipe = "sm"
        paket = "PAKET BISNIS KECIL"
        paketan = request.POST['bisnis_kecil']
        daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
    elif 'bisnis_medium' in request.POST:
        tipe = "med"
        paket = "PAKET BISNIS MEDIUM"
        paketan = request.POST['bisnis_medium']
        daftarpaket = DaftarPaket.objects.get(nama="Bisnis Medium")
    else:
        tipe = "tr"
        pkt  = 0
        paket = "PAKET DASAR"
        harga = 0
        jenis_paket = f"Gratis selamanya dengan maksimal {PAKET_GRATIS_KUOTA_BULANAN} transaksi per bulan"

    if daftarpaket:
        dur_map = {
            'bulanan':  (0, 0,   daftarpaket.harga_per_bulan,       f"1 Bulan mulai {now.strftime('%d-%m-%Y')}"),
            '3bulanan': (1, 91,  daftarpaket.harga_per_tiga_bulan,  f"3 Bulan mulai {now.strftime('%d-%m-%Y')} s.d. {(now+datetime.timedelta(weeks=13)).strftime('%d-%m-%Y')}"),
            '6bulanan': (2, 182, daftarpaket.harga_per_enam_bulan,  f"6 Bulan mulai {now.strftime('%d-%m-%Y')} s.d. {(now+datetime.timedelta(weeks=26)).strftime('%d-%m-%Y')}"),
            'tahunan':  (3, 365, daftarpaket.harga_per_tahun,       f"1 Tahun mulai {now.strftime('%d-%m-%Y')} s.d. {(now+datetime.timedelta(weeks=52)).strftime('%d-%m-%Y')}"),
        }
        item = dur_map.get(paketan)
        if item:
            pkt, _, harga, jenis_paket = item
        else:
            pkt = 4
            harga = daftarpaket.harga_per_dua_tahun
            jenis_paket = f"2 Tahun mulai {now.strftime('%d-%m-%Y')} s.d. {(now+datetime.timedelta(weeks=104)).strftime('%d-%m-%Y')}"

    pricing_options = []
    package_options = []
    if daftarpaket:
        pricing_options = [
            {'pkt': 0, 'value': 'bulanan',   'label': 'Per Bulan',   'duration': '1 Bulan',  'harga': daftarpaket.harga_per_bulan,      'note': 'Cocok untuk mulai mencoba.'},
            {'pkt': 1, 'value': '3bulanan',  'label': 'Per 3 Bulan', 'duration': '3 Bulan',  'harga': daftarpaket.harga_per_tiga_bulan, 'note': 'Lebih praktis untuk kuartalan.'},
            {'pkt': 2, 'value': '6bulanan',  'label': 'Per 6 Bulan', 'duration': '6 Bulan',  'harga': daftarpaket.harga_per_enam_bulan, 'note': 'Pilihan stabil setengah tahun.'},
            {'pkt': 3, 'value': 'tahunan',   'label': 'Per Tahun',   'duration': '1 Tahun',  'harga': daftarpaket.harga_per_tahun,      'note': 'Rekomendasi penggunaan rutin.'},
            {'pkt': 4, 'value': '2tahunan',  'label': 'Per 2 Tahun', 'duration': '2 Tahun',  'harga': daftarpaket.harga_per_dua_tahun,  'note': 'Paling tenang jangka panjang.'},
        ]
        for opt_tipe, opt_nama, opt_desk in [
            ('sm',  'Bisnis Kecil',  'Paket lincah untuk toko berkembang.'),
            ('med', 'Bisnis Medium', 'Paket lebih lega untuk operasional besar.'),
        ]:
            try:
                po = DaftarPaket.objects.get(nama=opt_nama)
                package_options.append({
                    'tipe': opt_tipe, 'nama': opt_nama, 'deskripsi': opt_desk,
                    'selected': tipe == opt_tipe,
                    'max_transaksi': po.max_transaksi, 'max_user_login': po.max_user_login,
                    'harga_per_bulan': po.harga_per_bulan, 'harga_per_tiga_bulan': po.harga_per_tiga_bulan,
                    'harga_per_enam_bulan': po.harga_per_enam_bulan, 'harga_per_tahun': po.harga_per_tahun,
                    'harga_per_dua_tahun': po.harga_per_dua_tahun,
                })
            except DaftarPaket.DoesNotExist:
                pass

    context = {
        'paket': paket, 'harga': harga, 'kode_toko': kode_toko,
        'jenis_paket': jenis_paket, 'tipe': tipe, 'pkt': pkt,
        'pricing_options': pricing_options, 'package_options': package_options,
    }
    if tipe == "tr":
        return render(request, 'registrasi/registrasi.html', context)
    return render(request, 'registrasi/registrasi_bayar.html', context)


def requestDemoAplikasi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = "/"

    if request.method != "POST":
        return HttpResponseRedirect('/')

    nama          = request.POST.get('nama', '').strip()
    email         = request.POST.get('email', '').strip().lower()
    aplikasi_demo = request.POST.get('aplikasi_demo', '').strip()
    keterangan    = request.POST.get('keterangan', '').strip()
    pilihan_aplikasi = dict(PermintaanKonsultasi.PILIHAN_APLIKASI)

    if not nama or not email or aplikasi_demo not in pilihan_aplikasi:
        messages.add_message(request, messages.SUCCESS,
            "Permintaan demo belum lengkap. Silakan isi nama, email, dan aplikasi.")
        return HttpResponseRedirect(asal)

    PermintaanKonsultasi.objects.create(
        nama=nama, email=email, jenis_permintaan='demo_aplikasi',
        aplikasi_demo=aplikasi_demo, keterangan=keterangan,
    )
    nama_aplikasi = pilihan_aplikasi[aplikasi_demo]
    posmiMail("PERMINTAAN DEMO APLIKASI",
        f"Permintaan Demo\n\nNama: {nama}\nEmail: {email}\nAplikasi: {nama_aplikasi}\n"
        f"Keterangan: {keterangan or '-'}\nTanggal: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        address="adhy.chandra@live.co.uk")
    posmiMail("Permintaan Demo Aplikasi Diterima",
        f"Halo {nama},\n\nTerima kasih sudah mengirimkan permintaan demo untuk {nama_aplikasi}. "
        f"Tim POSMI akan menghubungi Anda.\n\nSalam,\nSuryo Adhy Chandra",
        address=email)
    messages.add_message(request, messages.SUCCESS,
        "Permintaan demo aplikasi sudah terkirim. Kami akan segera menghubungi Sobat.")
    return HttpResponseRedirect(asal)


def paymentResponse(request):
    """Proses form registrasi → PendingPayment → Midtrans (atau langsung untuk paket gratis)."""
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = "/"

    pkt  = int(request.GET['pkt'])
    tipe = request.GET['tipe']

    # Hitung harga dan lisensi berdasarkan tipe & pkt
    lisensi_expired  = None
    harga            = 0
    jumlah_transaksi = 0
    daftarpaket      = None

    dur_days = {0: 30, 1: 91, 2: 182, 3: 365, 4: 730}

    if tipe == 'tr':
        jumlah_transaksi = PAKET_GRATIS_KUOTA_BULANAN
    elif tipe in ('sm', 'med'):
        nama_paket  = 'Bisnis Kecil' if tipe == 'sm' else 'Bisnis Medium'
        daftarpaket = DaftarPaket.objects.get(nama=nama_paket)
        jumlah_transaksi = daftarpaket.max_transaksi
        harga_field = {
            0: daftarpaket.harga_per_bulan,   1: daftarpaket.harga_per_tiga_bulan,
            2: daftarpaket.harga_per_enam_bulan, 3: daftarpaket.harga_per_tahun,
            4: daftarpaket.harga_per_dua_tahun,
        }
        harga = harga_field.get(pkt, 0)
        if pkt > 0:
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=dur_days.get(pkt, 30))

    if request.method != "POST":
        return HttpResponseRedirect(asal)

    voucher = request.POST.get('voucher', '').lower()
    if voucher:
        cek_voucher = cekKodeVoucher(kode=voucher, tipe="reg")
        if cek_voucher['status']:
            try:
                promo = Promo.objects.get(kode=voucher)
                harga = max(0, harga - promo.disc)
            except Exception:
                pass

    kode_toko    = request.POST.get('kode_toko', '')
    nama_toko    = request.POST.get('nama_toko', '')
    email_toko   = request.POST.get('email_toko', '')
    pemilik_toko = request.POST.get('pemilik_toko', '')
    password     = request.POST.get('password_admin', '')

    if Cabang.objects.filter(email=email_toko).exists():
        messages.add_message(request, messages.SUCCESS,
            'Pendaftaran Gagal: email sudah terdaftar. Gunakan email lain.')
        return HttpResponseRedirect(asal)

    lisensi_days = int((lisensi_expired - datetime.datetime.now()).days) if lisensi_expired else 0

    pending_data = {
        'tipe': tipe, 'pkt': pkt,
        'kode_toko': kode_toko, 'nama_toko': nama_toko,
        'nama_cabang': request.POST.get('nama_cabang', ''),
        'alamat_toko': request.POST.get('alamat_toko', ''),
        'telpon':      request.POST.get('telpon_toko', ''),
        'email_toko':  email_toko, 'pemilik_toko': pemilik_toko,
        'pw_hash':     _mkpw(password),
        'voucher':     voucher,
        'referensi':   request.POST.get('referensi', ''),
        'lisensi_days': lisensi_days,
        'jumlah_transaksi': jumlah_transaksi,
    }

    # Paket gratis → proses langsung
    if tipe == 'tr' or harga == 0:
        p = PendingPayment.objects.create(
            order_id=_buat_order_id('REG'),
            tipe=PendingPayment.TIPE_REGISTRASI,
            data=pending_data, harga=0,
            status=PendingPayment.STATUS_PAID,
        )
        _proses_pending_payment(p)
        messages.add_message(request, messages.SUCCESS,
            f"Akun toko {nama_toko} ({kode_toko}1) berhasil dibuat. Silakan login.")
        return HttpResponseRedirect('/')

    # Berbayar → Midtrans
    order_id   = _buat_order_id('REG')
    finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
    PendingPayment.objects.create(
        order_id=order_id, tipe=PendingPayment.TIPE_REGISTRASI,
        data=pending_data, harga=int(harga),
    )
    try:
        redirect_url = prosesPayment(order_id, int(harga),
                                     nama_pembeli=pemilik_toko, email_pembeli=email_toko,
                                     finish_url=finish_url)
        return HttpResponseRedirect(redirect_url)
    except Exception as ex:
        PendingPayment.objects.filter(order_id=order_id).delete()
        messages.add_message(request, messages.SUCCESS,
            'Gagal membuat transaksi pembayaran. Coba beberapa saat lagi.')
        return HttpResponseRedirect(asal)


# ══════════════════════════════════════════════════════════════════════════════
#  GARANSI REFUND
# ══════════════════════════════════════════════════════════════════════════════

def ajukanRefundGaransi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = "/cms/"

    if not request.user.is_authenticated:
        messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu.")
        return HttpResponseRedirect('/login/')

    if not request.user.is_superuser:
        messages.add_message(request, messages.SUCCESS, "Hanya admin toko yang dapat mengajukan refund.")
        return HttpResponseRedirect(asal)

    if request.method != "POST":
        return HttpResponseRedirect(asal)

    try:
        cabang  = request.user.userprofile.cabang
        garansi = GaransiRefund.objects.filter(cabang=cabang).order_by('-created_at').first()

        if garansi is None:
            messages.add_message(request, messages.SUCCESS, "Garansi refund belum tersedia untuk toko ini.")
            return HttpResponseRedirect(asal)

        if garansi.status != GaransiRefund.STATUS_ELIGIBLE:
            messages.add_message(request, messages.SUCCESS, "Pengajuan refund sudah pernah dibuat.")
            return HttpResponseRedirect(asal)

        if datetime.datetime.now() > garansi.batas_pengajuan:
            garansi.status = GaransiRefund.STATUS_EXPIRED
            garansi.save()
            messages.add_message(request, messages.SUCCESS, "Masa pengajuan refund sudah melewati 30 hari.")
            return HttpResponseRedirect(asal)

        jumlah_transaksi = Penjualan.objects.filter(
            cabang=cabang, is_paid=True, is_void=False,
            created_at__gte=garansi.tanggal_aktivasi,
            created_at__lte=datetime.datetime.now(),
        ).count()

        garansi.alasan = request.POST.get('alasan', '')
        garansi.jumlah_transaksi_saat_pengajuan = jumlah_transaksi
        garansi.requested_at = datetime.datetime.now()

        if jumlah_transaksi <= REFUND_AUTO_LIMIT_TRANSAKSI:
            garansi.status        = GaransiRefund.STATUS_DIAJUKAN_AUTO
            garansi.alur_pengajuan = GaransiRefund.ALUR_AUTO
            pesan = "Pengajuan auto refund berhasil dikirim. Tim POSMI akan memvalidasi dan memproses pengembalian dana."
        else:
            garansi.status        = GaransiRefund.STATUS_DIAJUKAN_MEDIASI
            garansi.alur_pengajuan = GaransiRefund.ALUR_MEDIASI
            pesan = "Pengajuan refund melalui jalur mediasi berhasil dikirim."

        garansi.save()
        messages.add_message(request, messages.SUCCESS, pesan)
    except Exception:
        messages.add_message(request, messages.SUCCESS,
            "Pengajuan refund belum dapat diproses. Silakan coba kembali atau hubungi tim POSMI.")

    return HttpResponseRedirect(asal)


# ══════════════════════════════════════════════════════════════════════════════
#  LISENSI & KUOTA
# ══════════════════════════════════════════════════════════════════════════════

def cekLisensi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = "/"

    try:
        kode_toko = request.POST['id']
        tipe      = request.GET['tipe']
        list_kuota = list(range(50, 1500, 50))
        list_biaya = []

        cabang = Cabang.objects.get(prefix=kode_toko)
        info_registrasi = ""

        if tipe in ("small", "medium"):
            info_registrasi = (
                "Perpanjangan Lisensi Bisnis Kecil" if tipe == "small"
                else "Perpanjangan Lisensi Bisnis Medium"
            )
        elif tipe == "upgrade":
            if cabang.paket is None:
                info_registrasi = "Upgrade ke Paket Bisnis Kecil atau Medium"
                for daftar in DaftarPaket.objects.filter(nama__in=['Bisnis Kecil', 'Bisnis Medium']):
                    list_biaya.append(_build_biaya(daftar, 0))
            elif cabang.paket.nama == "Bisnis Kecil":
                info_registrasi = "Upgrade ke Paket Bisnis Medium"
                sisa_hari = max(0, int((cabang.lisensi_expired - datetime.datetime.now()).days))
                sisa_uang = (cabang.paket.harga_per_tahun / 365) * sisa_hari
                for daftar in DaftarPaket.objects.filter(nama='Bisnis Medium'):
                    list_biaya.append(_build_biaya(daftar, sisa_uang))
            else:
                messages.add_message(request, messages.SUCCESS,
                    f"Paket {cabang.nama_toko} sudah Medium. Gunakan tambah kuota transaksi.")
                return HttpResponseRedirect('/')
        elif tipe == "kuota":
            info_registrasi = "Penambahan Kuota"

        context = {
            'kode_toko': kode_toko, 'cabang': cabang,
            'nama_admin': getAdmin(kode_toko),
            'info_registrasi': info_registrasi, 'tipe': tipe,
            'list_kuota': list_kuota, 'asal': asal,
            'list_biaya': list_biaya,
            'wallet': cabang.wallet,
        }
        return render(request, 'registrasi/cek_lisensi.html', context)

    except Cabang.DoesNotExist:
        messages.add_message(request, messages.SUCCESS, "Kode Toko Tidak Ditemukan.")
        redirect_map = {
            'small': '/#lisensismall', 'medium': '/#lisensimedium',
            'upgrade': '/#upgradepaket', 'kuota': '/#tambahkuota',
        }
        return HttpResponseRedirect(redirect_map.get(request.GET.get('tipe', ''), '/'))
    except Exception:
        messages.add_message(request, messages.SUCCESS, "Kode Toko Tidak Ditemukan.")
        return HttpResponseRedirect("/")


def _build_biaya(daftar, sisa_uang):
    """Helper: build daftar opsi biaya untuk satu paket."""
    data = {'id': str(daftar.paket), 'nama': daftar.nama, 'biaya': []}
    fields = [
        ('bulanan', '1 bulanan', daftar.harga_per_bulan),
        ('tigabulanan', '3 bulanan', daftar.harga_per_tiga_bulan),
        ('enambulanan', '6 bulanan', daftar.harga_per_enam_bulan),
        ('tahunan', '1 tahunan', daftar.harga_per_tahun),
        ('duatahunan', '2 tahunan', daftar.harga_per_dua_tahun),
    ]
    for nama, info, harga in fields:
        nilai = int(harga - sisa_uang)
        if nilai > 0:
            data['biaya'].append({'nama': nama, 'info': info, 'data': nilai})
    return data


def hitungBiayaKuota(request):
    try:
        jml = int(request.GET['jumlah_kuota'])
        return HttpResponse(f'<span>Perkiraan Biaya:</span> Rp {int(jml * 10000 / 50):,}.00')
    except Exception:
        return HttpResponse('<span>Perkiraan Biaya:</span> Rp 0.00')


def tambahKuota(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = '/'

    try:
        kode_toko    = request.GET['id']
        jumlah_kuota = int(request.POST['jumlah_kuota'])
        voucher      = request.POST.get('voucher', '').lower()
        cabang       = Cabang.objects.get(prefix=kode_toko)

        harga = jumlah_kuota * 10000 / 50
        if voucher:
            cek = cekKodeVoucher(kode=voucher, toko=kode_toko, tipe='add')
            if cek['status']:
                harga = max(1000, harga - cek['disc'])

        # Potongan wallet
        gunakan_wallet = request.POST.get('gunakan_wallet') == 'on'
        wallet_dipakai = 0
        if gunakan_wallet and cabang.wallet > 0:
            wallet_dipakai = min(cabang.wallet, int(harga))
            harga = max(0, int(harga) - wallet_dipakai)

        # Wallet menutup penuh → proses langsung tanpa Midtrans
        if int(harga) == 0 and wallet_dipakai > 0:
            order_id = _buat_order_id('KTQ')
            p = PendingPayment.objects.create(
                order_id=order_id, tipe=PendingPayment.TIPE_KUOTA,
                data={'kode_toko': kode_toko, 'jumlah_kuota': jumlah_kuota,
                      'voucher': voucher, 'referensi': cabang.kode_referal or '',
                      'wallet_dipakai': wallet_dipakai},
                harga=0, status=PendingPayment.STATUS_PAID,
            )
            _proses_pending_payment(p)
            messages.add_message(request, messages.SUCCESS,
                f'Berhasil! {jumlah_kuota} kuota ditambahkan. Wallet berkurang Rp {wallet_dipakai:,}.')
            return HttpResponseRedirect('/')

        # Bayar via Midtrans
        order_id   = _buat_order_id('KTQ')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_KUOTA,
            data={'kode_toko': kode_toko, 'jumlah_kuota': jumlah_kuota,
                  'voucher': voucher, 'referensi': cabang.kode_referal or '',
                  'wallet_dipakai': wallet_dipakai},
            harga=int(harga),
        )
        user_adm     = User.objects.get(username=f"{kode_toko}1")
        redirect_url = prosesPayment(order_id, int(harga),
                                     nama_pembeli=user_adm.first_name,
                                     email_pembeli=cabang.email or '',
                                     finish_url=finish_url)
        return HttpResponseRedirect(redirect_url)

    except Exception as ex:
        messages.add_message(request, messages.SUCCESS, 'Gagal membuat transaksi. Coba beberapa saat lagi.')
        try:
            asal = request.META['HTTP_REFERER']
        except Exception:
            asal = '/'
        return HttpResponseRedirect(asal)


def hitungExpired(request):
    try:
        kode_toko = request.GET['id']
        cabang    = Cabang.objects.get(prefix=kode_toko)
        metode    = str(request.GET['list_biaya']).split('^')[0]
        if not metode:
            return HttpResponse("")

        day = DAY_MAP.get(metode, 30)
        if cabang.lisensi_expired and cabang.lisensi_expired > datetime.datetime.now():
            tanggal_expired = cabang.lisensi_expired + datetime.timedelta(days=day)
        else:
            tanggal_expired = datetime.datetime.now() + datetime.timedelta(days=day)

        return HttpResponse(f"Lisensi akan berakhir: {tanggal_expired.strftime('%d/%m/%Y')}")
    except Exception:
        return HttpResponse("-")


def upgradeLisensi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = '/'

    try:
        kode_toko = request.GET['id']
        cabang    = Cabang.objects.get(prefix=kode_toko)
        raw       = str(request.POST['list_biaya'])
        metode    = raw.split('^')[0]
        paket_id  = raw.split('^')[1]
        paket     = DaftarPaket.objects.get(paket=paket_id)

        harga_map = {
            'bulanan': paket.harga_per_bulan, 'tigabulanan': paket.harga_per_tiga_bulan,
            'enambulanan': paket.harga_per_enam_bulan, 'tahunan': paket.harga_per_tahun,
            'duatahunan': paket.harga_per_dua_tahun,
        }
        harga = harga_map.get(metode, paket.harga_per_bulan)

        # Potongan wallet
        gunakan_wallet = request.POST.get('gunakan_wallet') == 'on'
        wallet_dipakai = 0
        if gunakan_wallet and cabang.wallet > 0:
            wallet_dipakai = min(cabang.wallet, int(harga))
            harga = max(0, int(harga) - wallet_dipakai)

        pending_data = {
            'kode_toko': kode_toko, 'paket_id': str(paket.paket),
            'metode': metode, 'day': DAY_MAP.get(metode, 30),
            'wallet_dipakai': wallet_dipakai,
        }

        # Wallet menutup penuh → proses langsung
        if int(harga) == 0 and wallet_dipakai > 0:
            order_id = _buat_order_id('UPG')
            p = PendingPayment.objects.create(
                order_id=order_id, tipe=PendingPayment.TIPE_UPGRADE,
                data=pending_data, harga=0,
                status=PendingPayment.STATUS_PAID,
            )
            _proses_pending_payment(p)
            messages.add_message(request, messages.SUCCESS,
                f'Berhasil! Paket {paket.nama} diperbarui. Wallet berkurang Rp {wallet_dipakai:,}.')
            return HttpResponseRedirect('/')

        # Bayar via Midtrans
        order_id   = _buat_order_id('UPG')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_UPGRADE,
            data=pending_data, harga=int(harga),
        )
        user_adm     = User.objects.get(username=f"{kode_toko}1")
        redirect_url = prosesPayment(order_id, int(harga),
                                     nama_pembeli=user_adm.first_name,
                                     email_pembeli=cabang.email or '',
                                     finish_url=finish_url)
        return HttpResponseRedirect(redirect_url)

    except Exception as ex:
        messages.add_message(request, messages.SUCCESS, 'Gagal membuat transaksi. Coba beberapa saat lagi.')
        return HttpResponseRedirect(asal)


# ══════════════════════════════════════════════════════════════════════════════
#  MIDTRANS WEBHOOK & FINISH
# ══════════════════════════════════════════════════════════════════════════════

def midtransNotifikasi(request):
    """Webhook server-to-server Midtrans. URL diset di Midtrans Dashboard → Notification URL."""
    try:
        data       = json.loads(request.body)
        order_id   = data.get('order_id', '')
        trx_status = data.get('transaction_status', '')
        fraud      = data.get('fraud_status', 'accept')
        gross      = data.get('gross_amount', '0')

        status_code = data.get('status_code', '')
        raw  = f"{order_id}{status_code}{gross}{settings.MIDTRANS_SERVER}"
        sign = hashlib.sha512(raw.encode()).hexdigest()
        if sign != data.get('signature_key', ''):
            return HttpResponse('Invalid signature', status=400)

        try:
            pending = PendingPayment.objects.get(order_id=order_id)
        except PendingPayment.DoesNotExist:
            return HttpResponse('Order not found', status=404)

        if pending.status == PendingPayment.STATUS_PAID:
            return HttpResponse('Already processed', status=200)

        paid = trx_status in ('capture', 'settlement') and fraud in ('accept', 'challenge')
        if paid:
            _proses_pending_payment(pending)
            pending.status  = PendingPayment.STATUS_PAID
            pending.paid_at = datetime.datetime.now()
        elif trx_status in ('cancel', 'deny', 'expire'):
            pending.status = PendingPayment.STATUS_FAILED
        pending.save()

        return HttpResponse('OK', status=200)
    except Exception:
        return HttpResponse('Error', status=500)


def paymentFinish(request):
    """Redirect dari Midtrans setelah pembayaran selesai."""
    order_id = request.GET.get('order_id', '')
    status   = request.GET.get('transaction_status', 'pending')

    pending = PendingPayment.objects.filter(order_id=order_id).first() if order_id else None
    paid    = (pending and pending.status == PendingPayment.STATUS_PAID) or status in ('capture', 'settlement')

    return render(request, 'payment/finish.html', {
        'paid': paid, 'order_id': order_id,
        'tipe': pending.tipe if pending else '',
        'status': status,
    })

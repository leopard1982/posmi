from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth import login, authenticate
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import datetime

from .models import Owner, TransferStok, KUOTA_PER_SLOT_BULANAN, HARGA_PER_SLOT_BULANAN, HARGA_PER_SLOT_3BULAN, HARGA_PER_SLOT_6BULAN, HARGA_PER_SLOT_TAHUNAN, HARGA_PER_SLOT_2TAHUN
from stock.models import Cabang, Barang, UploadBarang, UploadBarangList
from pos.models import Penjualan
from django.http import JsonResponse, FileResponse
from django.conf import settings
import os
import pandas

OWNER_SESSION_KEY = 'owner_user_id'

import string, random as _random
def generate_nomor_faktur():
    chars = string.ascii_uppercase + string.digits
    return ''.join(_random.choices(chars, k=10))


def _is_owner(user):
    return hasattr(user, 'owner_profile')


def _require_owner(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/owner/login/')
    if not _is_owner(request.user):
        messages.error(request, "Halaman ini hanya untuk pemilik Paket Korporasi.")
        return HttpResponseRedirect('/')
    return None


# ── Dashboard ──────────────────────────────────────────────────────────────

def dashboard(request):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    now = datetime.datetime.now()
    cabang_list = list(owner.cabang_korporasi.filter(is_gudang=False))

    # Data per toko bulan ini
    toko_data = []
    for cab in cabang_list:
        qs = Penjualan.objects.filter(
            cabang=cab, is_paid=True, is_void=False,
            tgl_bayar__month=now.month, tgl_bayar__year=now.year
        )
        trx_bulan  = qs.count()
        omzet_bulan = qs.aggregate(total=Sum('total'))['total'] or 0
        toko_data.append({
            'cabang': cab,
            'trx_bulan': trx_bulan,
            'omzet_bulan': omzet_bulan,
        })

    total_trx   = sum(d['trx_bulan'] for d in toko_data)
    total_omzet = sum(d['omzet_bulan'] for d in toko_data)

    # Leaderboard kasir tergiat bulan ini
    from django.contrib.auth.models import User as DjangoUser
    kasir_leaderboard = (
        Penjualan.objects
        .filter(cabang__in=cabang_list, is_paid=True, is_void=False,
                tgl_bayar__month=now.month, tgl_bayar__year=now.year)
        .values('user__id', 'user__first_name', 'user__username', 'cabang__nama_toko')
        .annotate(jumlah_trx=Count('nota'), total_omzet=Sum('total'))
        .order_by('-jumlah_trx')[:5]
    )

    # Leaderboard toko omzet terbanyak bulan ini (sudah ada di toko_data, tinggal sort)
    toko_leaderboard = sorted(toko_data, key=lambda d: d['omzet_bulan'], reverse=True)[:5]

    # Omzet 6 bulan terakhir — gabungan & per toko
    bulan_labels = []
    bulan_omzet  = []   # gabungan
    bulan_trx    = []
    BULAN_ID = ['','Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']

    # Warna per toko
    WARNA_TOKO = [
        'rgba(78,115,223,.75)', 'rgba(28,200,138,.75)', 'rgba(246,194,62,.75)',
        'rgba(231,74,59,.75)', 'rgba(54,185,204,.75)', 'rgba(133,135,150,.75)',
    ]

    # Inisialisasi data per toko
    per_toko_data = {cab.id: [] for cab in cabang_list}

    for i in range(5, -1, -1):
        tgl = now.replace(day=1) - datetime.timedelta(days=i * 28)
        bln, thn = tgl.month, tgl.year
        label = f"{BULAN_ID[bln]} {thn}"
        bulan_labels.append(label)

        qs_all = Penjualan.objects.filter(
            cabang__in=cabang_list, is_paid=True, is_void=False,
            tgl_bayar__month=bln, tgl_bayar__year=thn
        )
        bulan_omzet.append(int(qs_all.aggregate(total=Sum('total'))['total'] or 0))
        bulan_trx.append(qs_all.count())

        for cab in cabang_list:
            omzet_toko = Penjualan.objects.filter(
                cabang=cab, is_paid=True, is_void=False,
                tgl_bayar__month=bln, tgl_bayar__year=thn
            ).aggregate(total=Sum('total'))['total'] or 0
            per_toko_data[cab.id].append(int(omzet_toko))

    # Dataset per toko untuk Chart.js
    datasets_per_toko = []
    for idx, cab in enumerate(cabang_list):
        warna = WARNA_TOKO[idx % len(WARNA_TOKO)]
        datasets_per_toko.append({
            'label': cab.nama_toko,
            'data': per_toko_data[cab.id],
            'backgroundColor': warna,
            'borderColor': warna.replace('.75', '1'),
            'borderWidth': 2,
        })

    # Rata-rata per bulan (semua toko) untuk garis tengah
    n_toko = len(cabang_list) or 1
    avg_per_bulan = [round(v / n_toko) for v in bulan_omzet]

    context = {
        'owner': owner,
        'toko_data': toko_data,
        'total_trx': total_trx,
        'total_omzet': total_omzet,
        'kuota_per_slot': KUOTA_PER_SLOT_BULANAN,
        'bulan_labels': bulan_labels,
        'bulan_omzet': bulan_omzet,
        'bulan_trx': bulan_trx,
        'datasets_per_toko': datasets_per_toko,
        'avg_per_bulan': avg_per_bulan,
        'now': now,
        'kasir_leaderboard': kasir_leaderboard,
        'toko_leaderboard': toko_leaderboard,
    }
    return render(request, 'owner/dashboard.html', context)


# ── Register Owner ──────────────────────────────────────────────────────────

def registerOwner(request):
    if request.user.is_authenticated and _is_owner(request.user):
        return HttpResponseRedirect('/owner/')

    harga_info = {
        'bulanan': HARGA_PER_SLOT_BULANAN,
        '3bulanan': HARGA_PER_SLOT_3BULAN,
        '6bulanan': HARGA_PER_SLOT_6BULAN,
        'tahunan': HARGA_PER_SLOT_TAHUNAN,
        '2tahunan': HARGA_PER_SLOT_2TAHUN,
    }

    if request.method == 'POST':
        nama       = request.POST.get('nama', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        password   = request.POST.get('password', '')
        phone      = request.POST.get('phone', '').strip()
        jumlah_slot = int(request.POST.get('jumlah_slot', 1))
        durasi     = request.POST.get('durasi', 'bulanan')

        if not nama or not email or not password:
            messages.error(request, "Nama, email, dan password wajib diisi.")
            return render(request, 'owner/register.html', {'harga_info': harga_info})

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email sudah terdaftar. Gunakan email berbeda untuk akun Korporasi.")
            return render(request, 'owner/register.html', {'harga_info': harga_info})
        # Email tidak boleh sama dengan email toko yang terdaftar
        if Cabang.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email ini sudah dipakai sebagai email toko. Gunakan email berbeda untuk akun Korporasi.")
            return render(request, 'owner/register.html', {'harga_info': harga_info})

        harga_slot = harga_info.get(durasi, HARGA_PER_SLOT_BULANAN)
        total_harga = harga_slot * jumlah_slot

        # durasi → hari
        durasi_hari = {'bulanan': 30, '3bulanan': 90, '6bulanan': 180, 'tahunan': 365, '2tahunan': 730}
        hari = durasi_hari.get(durasi, 30)
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=hari)
        lisensi_grace   = lisensi_expired + datetime.timedelta(days=7)
        kuota_pool = jumlah_slot * KUOTA_PER_SLOT_BULANAN

        user = User()
        user.username = email
        user.email    = email
        user.first_name = nama
        user.is_active = True
        user.save()
        user.set_password(password)
        user.save()

        new_owner = Owner.objects.create(
            user=user,
            nama=nama,
            phone=phone,
            jumlah_slot=jumlah_slot,
            kuota_transaksi_pool=kuota_pool,
            lisensi_expired=lisensi_expired,
            lisensi_grace=lisensi_grace,
        )
        get_or_create_gudang(new_owner)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f"Akun Korporasi berhasil dibuat. Selamat datang, {nama}!")
        return HttpResponseRedirect('/owner/')

    return render(request, 'owner/register.html', {'harga_info': harga_info})


def _hapus_session_lain_owner(user, current_session_key):
    """Hapus semua session aktif milik user kecuali session saat ini."""
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get('_auth_user_id')) == str(user.pk) and session.session_key != current_session_key:
            session.delete()


# ── Login Owner ──────────────────────────────────────────────────────────────

def loginOwner(request):
    if request.user.is_authenticated and _is_owner(request.user):
        return HttpResponseRedirect('/owner/')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        # Coba autentikasi langsung (username = email untuk Owner)
        user = authenticate(request, username=email, password=password)
        # Kalau gagal, coba cari User berdasarkan email (untuk Owner yang username != email)
        if not user:
            try:
                candidate = User.objects.get(email__iexact=email)
                user = authenticate(request, username=candidate.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass
        if user and _is_owner(user):
            login(request, user)
            _hapus_session_lain_owner(user, request.session.session_key)
            return HttpResponseRedirect('/owner/')
        messages.error(request, "Email atau password salah, atau akun bukan Korporasi.")

    return render(request, 'owner/login.html')


def _durasi_hari(durasi):
    return {
        'bulanan': 30,
        '3bulanan': 90,
        '6bulanan': 180,
        'tahunan': 365,
        '2tahunan': 730,
    }.get(durasi, 30)


def _harga_info_owner():
    return {
        'bulanan': HARGA_PER_SLOT_BULANAN,
        '3bulanan': HARGA_PER_SLOT_3BULAN,
        '6bulanan': HARGA_PER_SLOT_6BULAN,
        'tahunan': HARGA_PER_SLOT_TAHUNAN,
        '2tahunan': HARGA_PER_SLOT_2TAHUN,
    }


def _tambah_masa_aktif_owner(owner, durasi):
    hari = _durasi_hari(durasi)
    sekarang = datetime.datetime.now()
    mulai = owner.lisensi_expired if owner.lisensi_expired and owner.lisensi_expired > sekarang else sekarang
    owner.lisensi_expired = mulai + datetime.timedelta(days=hari)
    owner.lisensi_grace = owner.lisensi_expired + datetime.timedelta(days=7)


def upgradePaketOwner(request):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    harga_info = _harga_info_owner()
    now = datetime.datetime.now()

    # Hitung sisa hari + harga prorata per slot
    sisa_hari = max(0, (owner.lisensi_expired - now).days) if owner.lisensi_expired and owner.lisensi_expired > now else 0
    harga_per_hari = HARGA_PER_SLOT_BULANAN / 30
    harga_per_slot_prorata = round(harga_per_hari * sisa_hari)

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'tambah_slot':
            jumlah_slot = max(1, int(request.POST.get('jumlah_slot', 1)))
            if sisa_hari <= 0:
                messages.error(request, "Langganan tidak aktif. Tidak bisa menambah slot.")
                return HttpResponseRedirect(request.path)
            total_harga = harga_per_slot_prorata * jumlah_slot
            owner.jumlah_slot += jumlah_slot
            owner.kuota_transaksi_pool += jumlah_slot * KUOTA_PER_SLOT_BULANAN
            owner.save()
            messages.success(
                request,
                f"Berhasil menambah {jumlah_slot} slot (sisa {sisa_hari} hari). "
                f"Total slot: {owner.jumlah_slot}. "
                f"Estimasi biaya: Rp {total_harga:,}."
            )

        elif aksi == 'perpanjang':
            durasi = request.POST.get('durasi', 'bulanan')
            harga_slot = harga_info.get(durasi, HARGA_PER_SLOT_BULANAN)
            _tambah_masa_aktif_owner(owner, durasi)
            owner.kuota_transaksi_pool = max(owner.kuota_transaksi_pool, owner.jumlah_slot * KUOTA_PER_SLOT_BULANAN)
            owner.save()
            total_harga = harga_slot * owner.jumlah_slot
            messages.success(
                request,
                f"Perpanjangan berhasil. Paket aktif sampai {owner.lisensi_expired.strftime('%d/%m/%Y')}. "
                f"Estimasi pembayaran Rp {total_harga:,}."
            )

        else:
            messages.error(request, "Aksi tidak dikenali.")

        return HttpResponseRedirect(request.path)

    return render(request, 'owner/upgrade.html', {
        'owner':                  owner,
        'active_menu':            'upgrade',
        'harga_info':             harga_info,
        'kuota_per_slot':         KUOTA_PER_SLOT_BULANAN,
        'sisa_hari':              sisa_hari,
        'harga_per_slot_prorata': harga_per_slot_prorata,
        'harga_per_hari':         round(harga_per_hari),
    })


# ── Daftarkan Toko Baru ke Korporasi ─────────────────────────────────────────

def klaimToko(request):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    from stock.models import prefixGenerator, UserProfile

    # Kode toko acak yang belum dipakai
    kode_preview = prefixGenerator()

    if request.method == 'POST':
        kode_toko      = request.POST.get('kode_toko', '').strip().lower()
        nama_toko      = request.POST.get('nama_toko', '').strip()
        nama_cabang    = request.POST.get('nama_cabang', '').strip() or 'Pusat'
        alamat_toko    = request.POST.get('alamat_toko', '').strip()
        telpon_toko    = request.POST.get('telpon_toko', '').strip()
        email_toko     = request.POST.get('email_toko', '').strip().lower()
        nama_admin     = request.POST.get('nama_admin', '').strip()
        password_admin = request.POST.get('password_admin', '')

        errors = []
        if not kode_toko or len(kode_toko) != 4:
            errors.append("Kode toko harus 4 huruf.")
        if not nama_toko:
            errors.append("Nama toko wajib diisi.")
        if not email_toko:
            errors.append("Email toko wajib diisi.")
        if not nama_admin:
            errors.append("Nama admin wajib diisi.")
        if len(password_admin) < 6:
            errors.append("Password minimal 6 karakter.")
        if owner.slot_tersedia <= 0:
            errors.append(f"Slot toko sudah penuh ({owner.jumlah_slot} slot).")
        if Cabang.objects.filter(prefix=kode_toko).exists():
            errors.append(f"Kode toko '{kode_toko}' sudah digunakan. Klik Acak untuk mendapat kode lain.")
        if User.objects.filter(email__iexact=email_toko).exists():
            errors.append(f"Email '{email_toko}' sudah terdaftar.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'owner/klaim_toko.html', {
                'owner': owner,
                'kode_preview': kode_toko or kode_preview,
                'form': request.POST,
            })

        # Buat Cabang
        cabang = Cabang()
        cabang.owner         = owner
        cabang.paket         = None
        cabang.nama_toko     = nama_toko
        cabang.nama_cabang   = nama_cabang
        cabang.alamat_toko   = alamat_toko or '-'
        cabang.telpon        = telpon_toko or '-'
        cabang.email         = email_toko
        cabang.prefix        = kode_toko
        cabang.lisensi_expired = None
        cabang.lisensi_grace   = None
        cabang.kuota_transaksi = 0  # pakai pool owner
        cabang.no_nota       = 1
        cabang.save()

        # Buat User admin toko
        admin_user = User()
        admin_user.username   = f"{kode_toko}1"
        admin_user.email      = email_toko
        admin_user.first_name = nama_admin
        admin_user.is_active  = True
        admin_user.is_superuser = True
        admin_user.save()
        admin_user.set_password(password_admin)
        admin_user.save()

        # Buat UserProfile
        UserProfile.objects.create(
            user=admin_user,
            cabang=cabang,
            nama_lengkap=nama_admin,
            is_active=True,
        )

        messages.success(request, (
            f"Toko '{nama_toko}' berhasil dibuat dan terdaftar dalam Paket Korporasi. "
            f"Admin dapat login dengan username: {kode_toko}1"
        ))
        return HttpResponseRedirect('/owner/')

    return render(request, 'owner/klaim_toko.html', {
        'owner': owner,
        'kode_preview': kode_preview,
        'form': {},
    })


# ── Lepas Toko dari Korporasi ────────────────────────────────────────────────

def lepasToko(request, cabang_id):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
        cabang.owner = None
        cabang.save()
        messages.success(request, f"Toko {cabang.nama_toko} berhasil dilepas dari Paket Korporasi.")
    except Cabang.DoesNotExist:
        messages.error(request, "Toko tidak ditemukan.")
    return HttpResponseRedirect('/owner/')


# ── Masuk ke Toko (impersonasi admin toko) ───────────────────────────────────

def masukToko(request, cabang_id):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
    except Cabang.DoesNotExist:
        messages.error(request, "Toko tidak ditemukan.")
        return HttpResponseRedirect('/owner/')

    try:
        admin_user = User.objects.get(username=f"{cabang.prefix}1")
    except User.DoesNotExist:
        messages.error(request, "Akun admin toko tidak ditemukan.")
        return HttpResponseRedirect('/owner/')

    request.session[OWNER_SESSION_KEY] = str(request.user.id)
    login(request, admin_user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f"Anda masuk sebagai admin toko {cabang.nama_toko}.")
    return HttpResponseRedirect('/cms/')


# ── Kembali ke Dashboard Owner ───────────────────────────────────────────────

def keluarToko(request):
    owner_user_id = request.session.get(OWNER_SESSION_KEY)
    if not owner_user_id:
        return HttpResponseRedirect('/')

    try:
        owner_user = User.objects.get(id=owner_user_id)
        del request.session[OWNER_SESSION_KEY]
        login(request, owner_user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Kembali ke Dashboard Korporasi.")
    except User.DoesNotExist:
        messages.error(request, "Sesi owner tidak ditemukan.")

    return HttpResponseRedirect('/owner/')


# ── Migrasi dari Paket Individual ke Korporasi ───────────────────────────────

def _get_owner_from_request(request):
    """Dapatkan Owner dari session (bisa via impersonasi dari CMS maupun login langsung)."""
    if _is_owner(request.user):
        return request.user.owner_profile
    owner_user_id = request.session.get(OWNER_SESSION_KEY)
    if owner_user_id:
        try:
            owner_user = User.objects.get(id=owner_user_id)
            return owner_user.owner_profile
        except (User.DoesNotExist, Exception):
            pass
    # User adalah admin toko yang berada di bawah Korporasi
    try:
        cabang = request.user.userprofile.cabang
        if cabang.owner_id:
            return cabang.owner
    except Exception:
        pass
    return None


# ── Transfer Stok ─────────────────────────────────────────────────────────────

def _eksekusi_transfer(transfer, approved_by):
    """Pindahkan stok setelah disetujui owner."""
    barang_asal = transfer.barang_asal
    try:
        barang_tujuan = Barang.objects.get(cabang=transfer.cabang_tujuan, barcode=barang_asal.barcode)
        barang_tujuan.stok += transfer.jumlah
        barang_tujuan.save()
    except Barang.DoesNotExist:
        # Buat master data dulu dengan stok=0, lalu tambahkan stok
        barang_tujuan = Barang.objects.create(
            cabang=transfer.cabang_tujuan,
            barcode=barang_asal.barcode,
            nama=barang_asal.nama,
            satuan=barang_asal.satuan,
            stok=0,
            harga_beli=barang_asal.harga_beli,
            harga_ecer=barang_asal.harga_ecer,
            harga_grosir=barang_asal.harga_grosir,
            min_beli_grosir=barang_asal.min_beli_grosir,
            keterangan=barang_asal.keterangan,
            created_by=approved_by,
        )
        barang_tujuan.stok += transfer.jumlah
        barang_tujuan.save()
    barang_asal.stok -= transfer.jumlah
    barang_asal.save()
    transfer.barang_tujuan = barang_tujuan
    transfer.status = TransferStok.STATUS_APPROVED
    transfer.approved_by = approved_by
    transfer.save()


def requestTransfer(request):
    """
    Admin toko membuat permintaan transfer dari /cms/.
    Stok belum bergerak — menunggu persetujuan owner.
    """
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/')

    owner = _get_owner_from_request(request)
    if not owner:
        messages.error(request, "Fitur transfer stok hanya tersedia untuk toko dalam Paket Korporasi.")
        return HttpResponseRedirect('/cms/')

    # Toko asal = toko user yang sedang login (atau pilihan jika owner langsung)
    try:
        cabang_user = request.user.userprofile.cabang
        is_store_admin = True
    except Exception:
        cabang_user = None
        is_store_admin = False

    cabang_list = list(owner.cabang_korporasi.filter(is_gudang=False))
    riwayat = TransferStok.objects.filter(
        owner=owner
    ).filter(
        cabang_asal=cabang_user
    ).order_by('-created_at')[:20] if cabang_user else []

    if request.method == 'POST':
        cabang_asal_id   = request.POST.get('cabang_asal') or (str(cabang_user.id) if cabang_user else None)
        cabang_tujuan_id = request.POST.get('cabang_tujuan')
        barang_id        = request.POST.get('barang_id')
        jumlah           = int(request.POST.get('jumlah', 0))
        catatan          = request.POST.get('catatan', '').strip()

        if str(cabang_asal_id) == str(cabang_tujuan_id):
            messages.error(request, "Toko asal dan toko tujuan tidak boleh sama.")
            return HttpResponseRedirect(request.path)
        if jumlah <= 0:
            messages.error(request, "Jumlah transfer harus lebih dari 0.")
            return HttpResponseRedirect(request.path)

        try:
            cabang_asal   = Cabang.objects.get(id=cabang_asal_id, owner=owner)
            cabang_tujuan = Cabang.objects.get(id=cabang_tujuan_id, owner=owner)
            barang_asal   = Barang.objects.get(id=barang_id, cabang=cabang_asal)
        except (Cabang.DoesNotExist, Barang.DoesNotExist):
            messages.error(request, "Data tidak valid.")
            return HttpResponseRedirect(request.path)

        if barang_asal.stok < jumlah:
            messages.error(request, f"Stok {barang_asal.nama} hanya {barang_asal.stok}, tidak cukup untuk transfer {jumlah}.")
            return HttpResponseRedirect(request.path)

        TransferStok.objects.create(
            owner=owner,
            cabang_asal=cabang_asal,
            cabang_tujuan=cabang_tujuan,
            barang_asal=barang_asal,
            jumlah=jumlah,
            catatan=catatan,
            nomor_faktur=generate_nomor_faktur(),
            status=TransferStok.STATUS_PENDING,
            created_by=request.user,
        )
        messages.success(request, f"Permintaan transfer {jumlah} {barang_asal.satuan} {barang_asal.nama} → {cabang_tujuan.nama_toko} telah dikirim. Menunggu persetujuan pemilik.")
        return HttpResponseRedirect(request.path)

    context = {
        'owner': owner,
        'cabang_list': cabang_list,
        'cabang_user': cabang_user,
        'is_store_admin': is_store_admin,
        'riwayat': riwayat,
    }
    return render(request, 'owner/request_transfer.html', context)


def approvalTransfer(request):
    """
    Owner melihat semua permintaan transfer dan menyetujui/menolak.
    Hanya bisa diakses oleh Owner langsung.
    """
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    pending = TransferStok.objects.filter(owner=owner, status=TransferStok.STATUS_PENDING).order_by('created_at')
    riwayat = TransferStok.objects.filter(owner=owner).exclude(status=TransferStok.STATUS_PENDING).order_by('-updated_at')[:30]

    if request.method == 'POST':
        transfer_id = request.POST.get('transfer_id')
        aksi        = request.POST.get('aksi')
        catatan_owner = request.POST.get('catatan_owner', '').strip()

        try:
            transfer = TransferStok.objects.get(id=transfer_id, owner=owner, status=TransferStok.STATUS_PENDING)
        except TransferStok.DoesNotExist:
            messages.error(request, "Permintaan transfer tidak ditemukan atau sudah diproses.")
            return HttpResponseRedirect(request.path)

        transfer.catatan_owner = catatan_owner

        if aksi == 'approve':
            if transfer.barang_asal.stok < transfer.jumlah:
                messages.error(request, f"Stok {transfer.barang_asal.nama} tidak cukup saat ini ({transfer.barang_asal.stok}). Transfer tidak bisa diproses.")
                return HttpResponseRedirect(request.path)
            _eksekusi_transfer(transfer, request.user)
            messages.success(request, f"Transfer {transfer.jumlah} {transfer.barang_asal.nama} dari {transfer.cabang_asal.nama_toko} → {transfer.cabang_tujuan.nama_toko} disetujui dan stok sudah dipindahkan.")
        elif aksi == 'reject':
            transfer.status = TransferStok.STATUS_REJECTED
            transfer.approved_by = request.user
            transfer.save()
            messages.warning(request, f"Permintaan transfer {transfer.barang_asal.nama} ditolak.")

        return HttpResponseRedirect(request.path)

    context = {
        'owner': owner,
        'pending': pending,
        'riwayat': riwayat,
    }
    return render(request, 'owner/approval_transfer.html', context)


def ajaxBarangCabang(request, cabang_id):
    """AJAX: kembalikan daftar barang (dengan stok > 0) dari sebuah cabang milik owner."""
    owner = _get_owner_from_request(request)
    if not owner:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
    except Cabang.DoesNotExist:
        return JsonResponse({'error': 'Toko tidak ditemukan'}, status=404)

    barang_list = Barang.objects.filter(cabang=cabang, stok__gt=0).order_by('nama').values(
        'id', 'nama', 'barcode', 'satuan', 'stok', 'harga_ecer'
    )
    return JsonResponse({'barang': list(barang_list)})


# ── Master Barang Korporasi ────────────────────────────────────────────────────

def _owner_or_cabang_owner(request):
    """Return (owner, cabang_user). cabang_user None jika akses sebagai owner murni."""
    if _is_owner(request.user):
        return request.user.owner_profile, None
    try:
        cab = request.user.userprofile.cabang
        if cab.owner_id:
            return cab.owner, cab
    except Exception:
        pass
    return None, None


def get_or_create_gudang(owner):
    """Dapatkan atau buat Gudang Utama untuk owner."""
    gudang = Cabang.objects.filter(owner=owner, is_gudang=True).first()
    if not gudang:
        from stock.models import prefixGenerator
        gudang = Cabang.objects.create(
            owner=owner,
            is_gudang=True,
            nama_toko=f"Gudang Utama",
            nama_cabang="Gudang",
            alamat_toko="-",
            telpon="-",
            email=owner.user.email,
            prefix=prefixGenerator(),
            paket=None,
            lisensi_expired=None,
            lisensi_grace=None,
            kuota_transaksi=0,
            no_nota=1,
        )
    return gudang


# ── Gudang Utama ───────────────────────────────────────────────────────────────

def gudangView(request):
    """Gudang Utama: kelola stok master + distribusi ke toko."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)
    toko_list = list(owner.cabang_korporasi.filter(is_gudang=False))
    barangs = Barang.objects.filter(cabang=gudang).order_by('nama')

    if request.method == 'POST' and request.POST.get('aksi') == 'hapus':
        try:
            b = Barang.objects.get(id=request.POST.get('barang_id'), cabang=gudang)
            nama = b.nama
            b.delete()
            messages.success(request, f"Barang '{nama}' berhasil dihapus dari Gudang Utama.")
        except Barang.DoesNotExist:
            messages.error(request, "Barang tidak ditemukan.")
        return HttpResponseRedirect(request.path)

    # Riwayat distribusi terbaru dari gudang
    from owner.models import TransferStok
    riwayat_distribusi = TransferStok.objects.filter(
        owner=owner, cabang_asal=gudang
    ).order_by('-created_at')[:20]

    context = {
        'owner': owner,
        'gudang': gudang,
        'toko_list': toko_list,
        'barangs': barangs,
        'jumlah_barang': barangs.count(),
        'riwayat_distribusi': riwayat_distribusi,
    }
    return render(request, 'owner/gudang.html', context)


def distribusiGudangKeToko(request):
    """Distribusi langsung dari Gudang Utama ke toko — tanpa approval."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)

    if request.method != 'POST':
        return HttpResponseRedirect('/owner/gudang/')

    barang_id        = request.POST.get('barang_id')
    cabang_tujuan_id = request.POST.get('cabang_tujuan')
    jumlah           = int(request.POST.get('jumlah', 0))
    catatan          = request.POST.get('catatan', '').strip()

    if jumlah <= 0:
        messages.error(request, "Jumlah distribusi harus lebih dari 0.")
        return HttpResponseRedirect('/owner/gudang/')

    try:
        barang_gudang = Barang.objects.get(id=barang_id, cabang=gudang)
        cabang_tujuan = Cabang.objects.get(id=cabang_tujuan_id, owner=owner, is_gudang=False)
    except (Barang.DoesNotExist, Cabang.DoesNotExist):
        messages.error(request, "Data tidak valid.")
        return HttpResponseRedirect('/owner/gudang/')

    if barang_gudang.stok < jumlah:
        messages.error(request, f"Stok gudang {barang_gudang.nama} hanya {barang_gudang.stok}.")
        return HttpResponseRedirect('/owner/gudang/')

    # Cari atau buat master data barang di toko tujuan (buat dengan stok=0 dulu)
    try:
        barang_tujuan = Barang.objects.get(cabang=cabang_tujuan, barcode=barang_gudang.barcode)
        barang_tujuan.stok += jumlah
        barang_tujuan.save()
    except Barang.DoesNotExist:
        barang_tujuan = Barang.objects.create(
            cabang=cabang_tujuan,
            barcode=barang_gudang.barcode,
            nama=barang_gudang.nama,
            satuan=barang_gudang.satuan,
            stok=0,
            harga_beli=barang_gudang.harga_beli,
            harga_ecer=barang_gudang.harga_ecer,
            harga_grosir=barang_gudang.harga_grosir,
            min_beli_grosir=barang_gudang.min_beli_grosir,
            keterangan=barang_gudang.keterangan,
            created_by=request.user,
        )

    # Kurangi stok gudang
    barang_gudang.stok -= jumlah
    barang_gudang.save()

    # Catat sebagai TransferStok (approved langsung)
    from owner.models import TransferStok
    TransferStok.objects.create(
        owner=owner,
        cabang_asal=gudang,
        cabang_tujuan=cabang_tujuan,
        barang_asal=barang_gudang,
        barang_tujuan=barang_tujuan,
        jumlah=jumlah,
        catatan=catatan or "Distribusi dari Gudang Utama",
        nomor_faktur=generate_nomor_faktur(),
        status=TransferStok.STATUS_APPROVED,
        approved_by=request.user,
        created_by=request.user,
    )

    messages.success(request, f"{jumlah} {barang_gudang.satuan} {barang_gudang.nama} berhasil didistribusikan ke {cabang_tujuan.nama_toko}.")
    return HttpResponseRedirect('/owner/gudang/')


# ── Pengiriman Gudang ke Toko ──────────────────────────────────────────────────

def buatPengiriman(request):
    """Owner membuat pengiriman dari gudang ke toko. Stok gudang langsung berkurang."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)

    if request.method != 'POST':
        return HttpResponseRedirect('/owner/gudang/')

    from owner.models import PengirimanGudang, PengirimanGudangItem

    # Support both field name conventions
    cabang_tujuan_id = request.POST.get('cabang_tujuan') or request.POST.get('toko_id') or request.POST.get('cabang_tujuan_id')
    nomor            = request.POST.get('nomor_pengiriman', '').strip().upper()
    catatan          = request.POST.get('catatan', '').strip()

    # Kumpulkan barang yang dicentang: field jumlah_<id> > 0
    barang_ids  = []
    jumlah_list = []
    for key, val in request.POST.items():
        if key.startswith('jumlah_'):
            try:
                bid = key[len('jumlah_'):]
                jml = int(val)
                if jml > 0:
                    barang_ids.append(bid)
                    jumlah_list.append(jml)
            except (ValueError, TypeError):
                continue
    # Fallback: jika pakai format lama (list)
    if not barang_ids:
        barang_ids = request.POST.getlist('barang_id')
        jumlah_list = [int(j) for j in request.POST.getlist('jumlah') if j.isdigit()]

    if not cabang_tujuan_id or not barang_ids:
        messages.error(request, "Pilih toko tujuan dan minimal 1 barang yang jumlahnya > 0.")
        return HttpResponseRedirect('/owner/distribusi/')

    try:
        cabang_tujuan = Cabang.objects.get(id=cabang_tujuan_id, owner=owner, is_gudang=False)
    except Cabang.DoesNotExist:
        messages.error(request, "Toko tujuan tidak valid.")
        return HttpResponseRedirect('/owner/distribusi/')

    if not nomor:
        nomor = generate_nomor_faktur()

    if PengirimanGudang.objects.filter(nomor_pengiriman=nomor).exists():
        nomor = generate_nomor_faktur()

    # Validasi stok sebelum membuat pengiriman
    errors = []
    items_valid = []
    for bid, jumlah in zip(barang_ids, jumlah_list):
        try:
            jumlah = int(jumlah)
            if jumlah <= 0:
                continue
            b = Barang.objects.get(id=bid, cabang=gudang)
            if b.stok < jumlah:
                errors.append(f"Stok {b.nama} di gudang hanya {b.stok}, tidak cukup untuk mengirim {jumlah}.")
            else:
                items_valid.append((b, jumlah))
        except (Barang.DoesNotExist, ValueError):
            continue

    if errors:
        for e in errors:
            messages.error(request, e)
        return HttpResponseRedirect('/owner/distribusi/')

    if not items_valid:
        messages.error(request, "Tidak ada barang valid untuk dikirim.")
        return HttpResponseRedirect('/owner/gudang/')

    # Buat pengiriman
    pengiriman = PengirimanGudang.objects.create(
        owner=owner,
        cabang_tujuan=cabang_tujuan,
        nomor_pengiriman=nomor,
        status=PengirimanGudang.STATUS_DIKIRIM,
        catatan=catatan,
        created_by=request.user,
    )

    # Buat item + kurangi stok gudang
    for barang_obj, jumlah in items_valid:
        PengirimanGudangItem.objects.create(
            pengiriman=pengiriman,
            barang_gudang=barang_obj,
            jumlah_dikirim=jumlah,
            status=PengirimanGudangItem.STATUS_PENDING,
        )
        barang_obj.stok -= jumlah
        barang_obj.save()

    messages.success(request, f"Pengiriman {nomor} ke {cabang_tujuan.nama_toko} berhasil dibuat. Stok gudang sudah dikurangi. Menunggu konfirmasi toko.")
    return HttpResponseRedirect(f'/owner/gudang/pengiriman/{pengiriman.id}/')


def daftarPengiriman(request):
    """Daftar semua pengiriman dari gudang."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    from owner.models import PengirimanGudang
    pengiriman_list = PengirimanGudang.objects.filter(owner=owner).order_by('-created_at')

    return render(request, 'owner/pengiriman/daftar.html', {
        'owner': owner,
        'pengiriman_list': pengiriman_list,
    })


def detailPengiriman(request, pengiriman_id):
    """Detail pengiriman + konfirmasi pengembalian barang ke gudang."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)
    from owner.models import PengirimanGudang, PengirimanGudangItem

    try:
        pengiriman = PengirimanGudang.objects.get(id=pengiriman_id, owner=owner)
    except PengirimanGudang.DoesNotExist:
        messages.error(request, "Pengiriman tidak ditemukan.")
        return HttpResponseRedirect('/owner/gudang/pengiriman/')

    if request.method == 'POST':
        item_id  = request.POST.get('item_id')
        catatan  = request.POST.get('catatan_gudang', '').strip()
        try:
            item = PengirimanGudangItem.objects.get(
                id=item_id, pengiriman=pengiriman,
                status=PengirimanGudangItem.STATUS_DIKEMBALIKAN
            )
            # Konfirmasi → stok gudang bertambah
            item.barang_gudang.stok += item.jumlah_dikirim - item.jumlah_diterima
            item.barang_gudang.save()
            item.status = PengirimanGudangItem.STATUS_KONFIRMASI_GUDANG
            item.catatan_gudang = catatan
            item.save()
            messages.success(request, f"Pengembalian {item.barang_gudang.nama} dikonfirmasi. Stok gudang bertambah {item.jumlah_dikirim - item.jumlah_diterima}.")
        except PengirimanGudangItem.DoesNotExist:
            messages.error(request, "Item tidak valid.")

        # Update status pengiriman jika semua selesai
        items = pengiriman.item_set.all()
        if not items.filter(status__in=[PengirimanGudangItem.STATUS_PENDING, PengirimanGudangItem.STATUS_DIKEMBALIKAN]).exists():
            if items.filter(status=PengirimanGudangItem.STATUS_KONFIRMASI_GUDANG).exists():
                pengiriman.status = PengirimanGudang.STATUS_SEBAGIAN
            else:
                pengiriman.status = PengirimanGudang.STATUS_SELESAI
            pengiriman.save()

        return HttpResponseRedirect(request.path)

    context = {
        'owner': owner,
        'pengiriman': pengiriman,
        'items': pengiriman.item_set.all(),
        'gudang': gudang,
    }
    return render(request, 'owner/pengiriman/detail.html', context)


def approvalMasterBarang(request):
    """Owner menyetujui/menolak request master barang dari toko."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)
    from owner.models import RequestMasterBarang

    if request.method == 'POST':
        req_id  = request.POST.get('req_id')
        aksi    = request.POST.get('aksi')
        catatan = request.POST.get('catatan_owner', '').strip()

        try:
            req = RequestMasterBarang.objects.get(id=req_id, owner=owner)
        except RequestMasterBarang.DoesNotExist:
            messages.error(request, "Request tidak ditemukan.")
            return HttpResponseRedirect(request.path)

        if aksi == 'reject':
            req.status = RequestMasterBarang.STATUS_REJECTED
            req.catatan_owner = catatan
            req.save()
            messages.warning(request, f"Request '{req.nama}' ditolak.")

        elif aksi == 'approve':
            # Cek apakah barcode sudah ada di gudang
            barcode_final = req.barcode_baru.strip() if req.barcode_baru else req.barcode
            if Barang.objects.filter(cabang=gudang, barcode=barcode_final).exists():
                req.status = RequestMasterBarang.STATUS_CONFLICT
                req.catatan_owner = catatan or "Barcode sudah ada di gudang. Ganti barcode baru."
                req.save()
                messages.error(request, f"Barcode {barcode_final} sudah ada di Gudang. Ganti barcode baru untuk barang '{req.nama}'.")
            else:
                Barang.objects.create(
                    cabang=gudang,
                    barcode=barcode_final,
                    nama=req.nama,
                    satuan=req.satuan,
                    stok=0,
                    harga_beli=req.harga_beli,
                    harga_ecer=req.harga_ecer,
                    harga_grosir=req.harga_grosir,
                    min_beli_grosir=req.min_beli_grosir,
                    keterangan=req.keterangan,
                    created_by=request.user,
                )
                req.status = RequestMasterBarang.STATUS_APPROVED
                req.catatan_owner = catatan
                req.barcode_baru = barcode_final
                req.save()
                messages.success(request, f"Barang '{req.nama}' (barcode: {barcode_final}) berhasil ditambahkan ke Gudang Utama.")

        elif aksi == 'set_barcode':
            # Owner mengganti barcode lalu konfirmasi simpan
            barcode_baru = request.POST.get('barcode_baru', '').strip()
            if not barcode_baru:
                messages.error(request, "Barcode baru tidak boleh kosong.")
            elif Barang.objects.filter(cabang=gudang, barcode=barcode_baru).exists():
                messages.error(request, f"Barcode {barcode_baru} juga sudah ada di gudang. Coba barcode lain.")
            else:
                Barang.objects.create(
                    cabang=gudang,
                    barcode=barcode_baru,
                    nama=req.nama,
                    satuan=req.satuan,
                    stok=0,
                    harga_beli=req.harga_beli,
                    harga_ecer=req.harga_ecer,
                    harga_grosir=req.harga_grosir,
                    min_beli_grosir=req.min_beli_grosir,
                    keterangan=req.keterangan,
                    created_by=request.user,
                )
                req.status = RequestMasterBarang.STATUS_APPROVED
                req.barcode_baru = barcode_baru
                req.catatan_owner = f"Barcode diganti dari {req.barcode} menjadi {barcode_baru}"
                req.save()
                messages.success(request, f"Barang '{req.nama}' disimpan dengan barcode baru: {barcode_baru}.")

        return HttpResponseRedirect(request.path)

    pending  = RequestMasterBarang.objects.filter(owner=owner, status=RequestMasterBarang.STATUS_PENDING).order_by('-created_at')
    conflict = RequestMasterBarang.objects.filter(owner=owner, status=RequestMasterBarang.STATUS_CONFLICT).order_by('-created_at')
    history  = RequestMasterBarang.objects.filter(
        owner=owner, status__in=[RequestMasterBarang.STATUS_APPROVED, RequestMasterBarang.STATUS_REJECTED]
    ).order_by('-updated_at')[:20]

    return render(request, 'owner/approval_master_barang.html', {
        'owner':    owner,
        'gudang':   gudang,
        'pending':  pending,
        'conflict': conflict,
        'history':  history,
    })


def monitoringStokToko(request):
    """Owner: monitoring stok barang di semua toko Korporasi."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)
    toko_list = list(owner.cabang_korporasi.filter(is_gudang=False))

    # Ambil semua barang dari gudang sebagai referensi
    barang_gudang = Barang.objects.filter(cabang=gudang).order_by('nama')

    # 1 query: semua barang di semua toko sekaligus → dict[(cabang_id, barcode)] = stok
    toko_ids = [t.id for t in toko_list]
    stok_dict = {}
    for b in Barang.objects.filter(cabang_id__in=toko_ids).values('cabang_id', 'barcode', 'stok'):
        stok_dict[(b['cabang_id'], b['barcode'])] = b['stok']

    monitoring_data = []
    for bg in barang_gudang:
        toko_stok = []
        for toko in toko_list:
            stok = stok_dict.get((toko.id, bg.barcode))
            toko_stok.append({'toko': toko, 'stok': stok or 0, 'ada': stok is not None})
        monitoring_data.append({
            'barang': bg,
            'toko_stok': toko_stok,
            'total_stok_toko': sum(t['stok'] for t in toko_stok),
        })

    context = {
        'owner': owner,
        'toko_list': toko_list,
        'monitoring_data': monitoring_data,
        'gudang': gudang,
    }
    return render(request, 'owner/monitoring_stok.html', context)


def distribusiView(request):
    """Halaman distribusi barang dari Gudang Utama ke toko (terpisah dari gudang)."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)
    toko_list = list(owner.cabang_korporasi.filter(is_gudang=False))
    barangs_gudang = Barang.objects.filter(cabang=gudang, stok__gt=0).order_by('nama')

    from owner.models import PengirimanGudang
    riwayat_distribusi = PengirimanGudang.objects.filter(owner=owner).order_by('-created_at')[:30]

    context = {
        'owner': owner,
        'gudang': gudang,
        'toko_list': toko_list,
        'barangs_gudang': barangs_gudang,
        'riwayat_distribusi': riwayat_distribusi,
    }
    return render(request, 'owner/distribusi.html', context)


def orderTokoView(request):
    """Halaman manajemen order barang dari toko — owner review dan proses."""
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    gudang = get_or_create_gudang(owner)

    from owner.models import OrderBarang, OrderBarangItem

    if request.method == 'POST':
        order_id     = request.POST.get('order_id')
        aksi         = request.POST.get('aksi')
        catatan_owner = request.POST.get('catatan_owner', '').strip()

        try:
            order = OrderBarang.objects.get(id=order_id, owner=owner)
        except OrderBarang.DoesNotExist:
            messages.error(request, "Order tidak ditemukan.")
            return HttpResponseRedirect(request.path)

        if aksi == 'tolak':
            order.status = OrderBarang.STATUS_DITOLAK
            order.catatan_owner = catatan_owner
            order.save()
            messages.success(request, f"Order {order.nomor_order} ditolak.")

        elif aksi == 'proses':
            # Cek stok gudang per item, set jumlah_disetujui — 1 query untuk semua barcode
            items = list(order.item_set.all())
            barcodes = [i.barcode for i in items]
            stok_gudang_map = {
                b['barcode']: b['stok']
                for b in Barang.objects.filter(cabang=gudang, barcode__in=barcodes).values('barcode', 'stok')
            }
            for item in items:
                stok = stok_gudang_map.get(item.barcode, 0)
                item.stok_gudang = stok
                item.jumlah_disetujui = min(item.jumlah_order, stok)
                item.catatan = '' if item.jumlah_disetujui >= item.jumlah_order else f"Stok gudang hanya {stok}, dikirim {item.jumlah_disetujui}"
                item.save()
            order.status = OrderBarang.STATUS_DIPROSES
            order.catatan_owner = catatan_owner
            order.save()
            messages.success(request, f"Order {order.nomor_order} siap diproses. Tinjau item dan konfirmasi distribusi.")

        elif aksi == 'distribusikan':
            # Eksekusi distribusi dari gudang ke toko berdasarkan order
            from owner.models import PengirimanGudang, PengirimanGudangItem
            items = order.item_set.filter(jumlah_disetujui__gt=0)
            if not items.exists():
                messages.error(request, "Tidak ada item dengan jumlah disetujui > 0.")
                return HttpResponseRedirect(request.path)

            nomor_pengiriman = generate_nomor_faktur()
            pengiriman = PengirimanGudang.objects.create(
                owner=owner,
                cabang_tujuan=order.cabang,
                nomor_pengiriman=nomor_pengiriman,
                status=PengirimanGudang.STATUS_DIKIRIM,
                catatan=f"Dari order {order.nomor_order}",
                created_by=request.user,
            )
            for item in items:
                try:
                    bg = Barang.objects.get(cabang=gudang, barcode=item.barcode)
                    if bg.stok >= item.jumlah_disetujui:
                        PengirimanGudangItem.objects.create(
                            pengiriman=pengiriman,
                            barang_gudang=bg,
                            jumlah_dikirim=item.jumlah_disetujui,
                            status=PengirimanGudangItem.STATUS_PENDING,
                        )
                        bg.stok -= item.jumlah_disetujui
                        bg.save()
                except Barang.DoesNotExist:
                    continue

            order.status = OrderBarang.STATUS_DIKIRIM
            order.save()
            messages.success(request, f"Order {order.nomor_order} didistribusikan dengan no. pengiriman {nomor_pengiriman}.")

        return HttpResponseRedirect(request.path)

    # GET: tampilkan semua order
    orders_pending  = OrderBarang.objects.filter(owner=owner, status=OrderBarang.STATUS_PENDING).order_by('-created_at')
    orders_diproses = OrderBarang.objects.filter(owner=owner, status=OrderBarang.STATUS_DIPROSES).order_by('-created_at')
    orders_selesai  = OrderBarang.objects.filter(
        owner=owner, status__in=[OrderBarang.STATUS_DIKIRIM, OrderBarang.STATUS_DITOLAK]
    ).order_by('-created_at')[:20]

    context = {
        'owner': owner,
        'gudang': gudang,
        'orders_pending': orders_pending,
        'orders_diproses': orders_diproses,
        'orders_selesai': orders_selesai,
    }
    return render(request, 'owner/order_toko.html', context)


def barangIndex(request):
    """Tampilkan Gudang Utama barang."""
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        messages.error(request, "Fitur ini hanya untuk Paket Korporasi.")
        return HttpResponseRedirect('/')
    gudang = get_or_create_gudang(owner)
    return HttpResponseRedirect(f'/owner/gudang/')


def barangToko(request, cabang_id):
    """Daftar barang per toko — read-only, hanya tampilkan stok dan tombol transfer dari gudang."""
    owner, cabang_user = _owner_or_cabang_owner(request)
    if not owner:
        messages.error(request, "Fitur ini hanya untuk Paket Korporasi.")
        return HttpResponseRedirect('/')
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner, is_gudang=False)
    except Cabang.DoesNotExist:
        # Jika cabang adalah gudang utama, redirect ke halaman gudang tanpa error
        return HttpResponseRedirect('/owner/gudang/')

    cabang_list = list(owner.cabang_korporasi.filter(is_gudang=False))
    barangs = Barang.objects.filter(cabang=cabang).order_by('nama')
    gudang = get_or_create_gudang(owner)

    context = {
        'owner': owner,
        'cabang': cabang,
        'cabang_list': cabang_list,
        'barangs': barangs,
        'jumlah_barang': barangs.count(),
        'is_store_admin': cabang_user is not None,
        'gudang': gudang,
    }
    return render(request, 'owner/barang/list_toko.html', context)


def tambahBarangOwner(request, cabang_id=None):
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        return HttpResponseRedirect('/')
    # Jika tidak ada cabang_id atau cabang_id merujuk ke gudang, gunakan gudang utama
    if not cabang_id:
        cabang = get_or_create_gudang(owner)
    else:
        try:
            cabang = Cabang.objects.get(id=cabang_id, owner=owner)
        except Cabang.DoesNotExist:
            messages.error(request, "Toko tidak ditemukan.")
            return HttpResponseRedirect('/owner/')

    if request.method == 'POST':
        barcode   = request.POST.get('barcode', '').strip()
        nama      = request.POST.get('nama', '').strip()
        satuan    = request.POST.get('satuan', 'PCS')
        stok      = int(request.POST.get('stok', 0))
        harga_beli   = int(request.POST.get('harga_beli', 0))
        harga_ecer   = int(request.POST.get('harga_ecer', 0))
        harga_grosir = int(request.POST.get('harga_grosir', 0))
        min_beli_grosir = int(request.POST.get('min_beli_grosir', 0))
        keterangan = request.POST.get('keterangan', '').strip()

        if not barcode or not nama:
            messages.error(request, "Barcode dan nama barang wajib diisi.")
            return HttpResponseRedirect(request.path)

        if Barang.objects.filter(cabang=cabang, barcode=barcode).exists():
            messages.error(request, f"Barcode {barcode} sudah digunakan di toko ini.")
            return HttpResponseRedirect(request.path)

        Barang.objects.create(
            cabang=cabang, barcode=barcode, nama=nama, satuan=satuan,
            stok=stok, harga_beli=harga_beli, harga_ecer=harga_ecer,
            harga_grosir=harga_grosir, min_beli_grosir=min_beli_grosir,
            keterangan=keterangan, created_by=request.user,
        )
        redirect_url = '/owner/gudang/' if cabang.is_gudang else f'/owner/barang/{cabang.id}/'
        messages.success(request, f"Barang '{nama}' berhasil ditambahkan ke {cabang.nama_toko}.")
        return HttpResponseRedirect(redirect_url)

    return render(request, 'owner/barang/tambah.html', {
        'owner': owner, 'cabang': cabang,
        'cabang_list': list(owner.cabang_korporasi.filter(is_gudang=False)),
        'is_gudang': cabang.is_gudang,
    })


def editBarangOwner(request, cabang_id, barang_id):
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        return HttpResponseRedirect('/')
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
        barang = Barang.objects.get(id=barang_id, cabang=cabang)
    except (Cabang.DoesNotExist, Barang.DoesNotExist):
        messages.error(request, "Data tidak ditemukan.")
        return HttpResponseRedirect(f'/owner/barang/{cabang_id}/')

    if request.method == 'POST':
        barang.nama         = request.POST.get('nama', barang.nama).strip()
        barang.satuan       = request.POST.get('satuan', barang.satuan)
        barang.stok         = int(request.POST.get('stok', barang.stok))
        barang.harga_beli   = int(request.POST.get('harga_beli', barang.harga_beli))
        barang.harga_ecer   = int(request.POST.get('harga_ecer', barang.harga_ecer))
        barang.harga_grosir = int(request.POST.get('harga_grosir', barang.harga_grosir))
        barang.min_beli_grosir = int(request.POST.get('min_beli_grosir', barang.min_beli_grosir))
        barang.keterangan   = request.POST.get('keterangan', '').strip()
        barang.save()
        messages.success(request, f"Barang '{barang.nama}' berhasil diperbarui.")
        return HttpResponseRedirect(f'/owner/barang/{cabang_id}/')

    return render(request, 'owner/barang/edit.html', {
        'owner': owner, 'cabang': cabang, 'barang': barang,
        'cabang_list': list(owner.cabang_korporasi.filter(is_gudang=False)),
    })


def uploadBarangOwner(request, cabang_id=None):
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        return HttpResponseRedirect('/')
    if not cabang_id:
        cabang = get_or_create_gudang(owner)
    else:
        try:
            cabang = Cabang.objects.get(id=cabang_id, owner=owner)
        except Cabang.DoesNotExist:
            messages.error(request, "Toko tidak ditemukan.")
            return HttpResponseRedirect('/owner/')

    if request.method == 'POST' and request.FILES.get('file'):
        try:
            df = pandas.read_excel(request.FILES['file'])
            uploadbarang = UploadBarang.objects.create(cabang=cabang, user=request.user)
            list_preview = []
            for _, row in df.iterrows():
                try:
                    barcode = str(int(row['barcode']))
                    nama    = str(row['nama'])
                    satuan  = str(row.get('satuan', 'PCS')).upper()
                    stok    = int(row.get('stok', 0)) if str(row.get('stok', 0)) != 'nan' else 0
                    harga_ecer   = int(row.get('harga_ecer', 0)) if str(row.get('harga_ecer', 0)) != 'nan' else 0
                    harga_grosir = int(row.get('harga_grosir', 0)) if str(row.get('harga_grosir', 0)) != 'nan' else 0
                    harga_beli   = int(row.get('harga_beli', 0)) if str(row.get('harga_beli', 0)) != 'nan' else 0
                    min_beli     = int(row.get('min_beli_grosir', 0)) if str(row.get('min_beli_grosir', 0)) != 'nan' else 0
                    keterangan   = str(row.get('keterangan', '')) if str(row.get('keterangan', '')) != 'nan' else ''
                    UploadBarangList.objects.create(
                        upload_barang=uploadbarang, barcode=barcode, nama=nama,
                        satuan=satuan, stok=stok, harga_ecer=harga_ecer,
                        harga_grosir=harga_grosir, harga_beli=harga_beli,
                        min_beli_grosir=min_beli, keterangan=keterangan,
                    )
                    list_preview.append({'barcode': barcode, 'nama': nama, 'satuan': satuan, 'stok': stok, 'harga_ecer': harga_ecer})
                except Exception:
                    continue
            return render(request, 'owner/barang/upload_preview.html', {
                'owner': owner, 'cabang': cabang,
                'list_preview': list_preview,
                'id_upload': str(uploadbarang.id_upload),
                'cabang_list': list(owner.cabang_korporasi.filter(is_gudang=False)),
            })
        except Exception as e:
            messages.error(request, f"Gagal membaca file: {e}")

    return render(request, 'owner/barang/upload.html', {
        'owner': owner, 'cabang': cabang,
        'cabang_list': list(owner.cabang_korporasi.filter(is_gudang=False)),
    })


def konfirmasiUploadOwner(request, cabang_id):
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        return HttpResponseRedirect('/')
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
    except Cabang.DoesNotExist:
        return HttpResponseRedirect('/owner/')

    id_upload = request.GET.get('id')
    try:
        uploadbarang = UploadBarang.objects.get(id_upload=id_upload, cabang=cabang)
        rows = UploadBarangList.objects.filter(upload_barang=uploadbarang)
        for row in rows:
            try:
                b = Barang.objects.get(cabang=cabang, barcode=row.barcode)
                b.satuan=row.satuan; b.stok=row.stok; b.harga_ecer=row.harga_ecer
                b.harga_grosir=row.harga_grosir; b.min_beli_grosir=row.min_beli_grosir
                b.harga_beli=row.harga_beli; b.keterangan=row.keterangan; b.save()
            except Barang.DoesNotExist:
                Barang.objects.create(
                    cabang=cabang, barcode=row.barcode, nama=row.nama,
                    satuan=row.satuan, stok=row.stok, harga_ecer=row.harga_ecer,
                    harga_grosir=row.harga_grosir, min_beli_grosir=row.min_beli_grosir,
                    harga_beli=row.harga_beli, keterangan=row.keterangan, created_by=request.user,
                )
        uploadbarang.delete()
        messages.success(request, f"{rows.count()} barang berhasil diupdate/ditambahkan ke {cabang.nama_toko}.")
    except Exception as e:
        messages.error(request, f"Gagal konfirmasi upload: {e}")
    # Redirect ke gudang jika cabang adalah gudang utama
    if cabang.is_gudang:
        return HttpResponseRedirect('/owner/gudang/')
    return HttpResponseRedirect(f'/owner/barang/{cabang_id}/')


def downloadTemplateOwner(request):
    lokasi = os.path.join(settings.BASE_DIR, 'static/template/template.xlsx')
    return FileResponse(open(lokasi, 'rb'), as_attachment=True, filename="template_barang.xlsx")


def downloadBarangOwner(request, cabang_id):
    """Download daftar barang toko sebagai Excel."""
    import openpyxl
    from django.http import HttpResponse
    owner, _ = _owner_or_cabang_owner(request)
    if not owner:
        return HttpResponseRedirect('/')
    try:
        cabang = Cabang.objects.get(id=cabang_id, owner=owner)
    except Cabang.DoesNotExist:
        return HttpResponseRedirect('/owner/')

    barangs = Barang.objects.filter(cabang=cabang).order_by('nama')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = cabang.nama_toko[:30]
    headers = ['barcode', 'nama', 'satuan', 'stok', 'harga_beli', 'harga_ecer', 'harga_grosir', 'min_beli_grosir', 'keterangan']
    ws.append(headers)
    for b in barangs:
        ws.append([b.barcode, b.nama, b.satuan, b.stok, b.harga_beli, b.harga_ecer, b.harga_grosir, b.min_beli_grosir, b.keterangan or ''])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="barang_{cabang.prefix}.xlsx"'
    wb.save(response)
    return response


# ── Manajemen Toko ────────────────────────────────────────────────────────────

def manajemenToko(request):
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile
    from stock.models import UserProfile

    if request.method == 'POST':
        aksi      = request.POST.get('aksi')
        cabang_id = request.POST.get('cabang_id')

        try:
            cabang = Cabang.objects.get(id=cabang_id, owner=owner)
        except Cabang.DoesNotExist:
            messages.error(request, "Toko tidak ditemukan.")
            return HttpResponseRedirect(request.path)

        if aksi == 'toggle_aktif':
            cabang.is_active = not cabang.is_active
            cabang.save()
            status = "diaktifkan" if cabang.is_active else "dinonaktifkan"
            messages.success(request, f"Toko '{cabang.nama_toko}' berhasil {status}.")

        elif aksi == 'ganti_password':
            pw_baru = request.POST.get('password_baru', '')
            if len(pw_baru) < 6:
                messages.error(request, "Password minimal 6 karakter.")
            else:
                try:
                    admin_user = User.objects.get(username=f"{cabang.prefix}1")
                    admin_user.set_password(pw_baru)
                    admin_user.save()
                    messages.success(request, f"Password admin toko '{cabang.nama_toko}' berhasil diganti.")
                except User.DoesNotExist:
                    messages.error(request, "Akun admin toko tidak ditemukan.")

        elif aksi == 'update_cabang':
            cabang.nama_toko   = request.POST.get('nama_toko', cabang.nama_toko).strip()
            cabang.nama_cabang = request.POST.get('nama_cabang', cabang.nama_cabang).strip()
            cabang.alamat_toko = request.POST.get('alamat_toko', cabang.alamat_toko).strip()
            cabang.telpon      = request.POST.get('telpon', cabang.telpon).strip()
            cabang.save()
            messages.success(request, f"Informasi toko '{cabang.nama_toko}' berhasil diperbarui.")

        elif aksi == 'ganti_email_toko':
            email_baru = request.POST.get('email_baru', '').strip().lower()
            if not email_baru:
                messages.error(request, "Email baru tidak boleh kosong.")
            elif User.objects.filter(email__iexact=email_baru).exclude(
                id=User.objects.filter(username=f"{cabang.prefix}1").values_list('id', flat=True).first()
            ).exists():
                messages.error(request, f"Email {email_baru} sudah dipakai di aplikasi POSMI.")
            else:
                cabang.email = email_baru
                cabang.save()
                try:
                    admin_user = User.objects.get(username=f"{cabang.prefix}1")
                    admin_user.email = email_baru
                    admin_user.save()
                except User.DoesNotExist:
                    pass
                messages.success(request, f"Email toko '{cabang.nama_toko}' berhasil diubah ke {email_baru}.")

        elif aksi == 'kurangi_slot':
            jumlah_kurangi = max(1, int(request.POST.get('jumlah_kurangi', 1)))
            new_slot = max(owner.slot_terpakai, owner.jumlah_slot - jumlah_kurangi)
            if new_slot >= owner.jumlah_slot:
                messages.error(request, "Tidak bisa mengurangi slot — semua slot sudah terpakai oleh toko.")
            else:
                owner.jumlah_slot = new_slot
                owner.save()
                messages.success(request, f"Slot Korporasi berkurang menjadi {new_slot} slot.")
            return HttpResponseRedirect(request.path)

        return HttpResponseRedirect(request.path)

    q = request.GET.get('q', '').strip()
    cabang_list = owner.cabang_korporasi.filter(is_gudang=False).order_by('nama_toko', 'nama_cabang')
    if q:
        cabang_list = cabang_list.filter(
            Q(nama_toko__icontains=q) |
            Q(nama_cabang__icontains=q)
        )

    paginator = Paginator(cabang_list, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    toko_data = []
    for cab in page_obj:
        try:
            admin_user = User.objects.get(username=f"{cab.prefix}1")
        except User.DoesNotExist:
            admin_user = None
        toko_data.append({'cabang': cab, 'admin': admin_user})

    return render(request, 'owner/manajemen_toko.html', {
        'owner': owner,
        'toko_data': toko_data,
        'page_obj': page_obj,
        'q': q,
        'total_toko': paginator.count,
    })


def downgradeKorporasi(request):
    """
    Downgrade dari Korporasi:
    1. Kurangi jumlah slot
    2. Pindah kembali ke individual (semua toko dilepas dari Korporasi)
    """
    redirect = _require_owner(request)
    if redirect:
        return redirect

    owner = request.user.owner_profile

    if request.method == 'POST':
        aksi = request.POST.get('aksi')

        if aksi == 'lepas_toko':
            # Lepas satu toko dari Korporasi → jadi gratis
            cabang_id = request.POST.get('cabang_id')
            try:
                cab = Cabang.objects.get(id=cabang_id, owner=owner, is_gudang=False)
                nama_toko = cab.nama_toko
                cab.owner = None
                cab.paket = None
                cab.lisensi_expired = None
                cab.lisensi_grace   = None
                cab.kuota_transaksi = 75
                cab.save()
                # Kurangi slot sesuai toko yang dilepas
                if owner.jumlah_slot > 0:
                    owner.jumlah_slot = max(owner.slot_terpakai, owner.jumlah_slot - 1)
                    owner.save()
                messages.success(request, f"Toko '{nama_toko}' berhasil dilepas dari Korporasi dan kembali ke Paket Gratis (75 transaksi/bulan). Tidak ada cashback pengembalian.")
            except Cabang.DoesNotExist:
                messages.error(request, "Toko tidak ditemukan.")

        elif aksi == 'kurangi_slot':
            jumlah_kurangi = max(1, int(request.POST.get('jumlah_kurangi', 1)))
            new_slot = owner.jumlah_slot - jumlah_kurangi
            if new_slot < owner.slot_terpakai:
                messages.error(request, f"Tidak bisa mengurangi ke {new_slot} slot — ada {owner.slot_terpakai} toko aktif. Lepas toko terlebih dahulu.")
            elif new_slot < 1:
                messages.error(request, "Jumlah slot minimal 1.")
            else:
                owner.jumlah_slot = new_slot
                owner.save()
                messages.success(request, f"Slot Korporasi dikurangi menjadi {new_slot} slot. Tidak ada cashback pengembalian.")

        elif aksi == 'downgrade_individual':
            konfirmasi = request.POST.get('konfirmasi', '')
            if konfirmasi != 'DOWNGRADE':
                messages.error(request, "Ketik DOWNGRADE untuk konfirmasi.")
            else:
                from django.db import transaction as _tx
                from django.contrib.auth import logout as auth_logout
                from owner.models import TransferStok, PengirimanGudang, OrderBarang, RequestMasterBarang

                try:
                    with _tx.atomic():
                        owner_user = owner.user

                        # Hitung toko sebelum diubah
                        toko_list = list(owner.cabang_korporasi.filter(is_gudang=False))
                        jumlah_toko = len(toko_list)

                        # ── Urutan hapus sesuai dependency FK ──
                        # 1. PengirimanGudang → CASCADE ke PengirimanGudangItem (yg RESTRICT ke Barang)
                        PengirimanGudang.objects.filter(owner=owner).delete()

                        # 2. TransferStok → RESTRICT ke Barang
                        TransferStok.objects.filter(owner=owner).delete()

                        # 3. OrderBarang + RequestMasterBarang
                        OrderBarang.objects.filter(owner=owner).delete()
                        RequestMasterBarang.objects.filter(owner=owner).delete()

                        # 4. Hapus Barang gudang (bukan barang toko)
                        for gudang in owner.cabang_korporasi.filter(is_gudang=True):
                            Barang.objects.filter(cabang=gudang).delete()
                            gudang.delete()

                        # 5. Lepas toko → paket gratis, barang toko tetap ada
                        for cab in toko_list:
                            cab.owner = None
                            cab.paket = None
                            cab.lisensi_expired = None
                            cab.lisensi_grace   = None
                            cab.kuota_transaksi = 75
                            cab.save()

                        # 6. Hapus Owner & user-nya
                        owner.delete()
                        owner_user.delete()

                    auth_logout(request)
                    messages.success(request,
                        f"Downgrade berhasil. {jumlah_toko} toko kembali ke Paket Gratis "
                        f"(75 transaksi/bulan). Akun Korporasi telah dihapus.")
                    return HttpResponseRedirect('/')

                except Exception as e:
                    messages.error(request, f"Downgrade gagal: {e}. Tidak ada perubahan yang tersimpan.")

        return HttpResponseRedirect(request.path)

    context = {
        'owner': owner,
        'toko_list': owner.cabang_korporasi.filter(is_gudang=False),
        'active_menu': 'downgrade',
    }
    return render(request, 'owner/downgrade.html', context)


def migrasiKeKorporasi(request):
    """
    Form publik: pemilik toko individual upgrade ke Paket Korporasi.
    Tidak perlu login dulu — verifikasi via kode toko + password admin.
    """
    harga_info = {
        'bulanan':   HARGA_PER_SLOT_BULANAN,
        '3bulanan':  HARGA_PER_SLOT_3BULAN,
        '6bulanan':  HARGA_PER_SLOT_6BULAN,
        'tahunan':   HARGA_PER_SLOT_TAHUNAN,
        '2tahunan':  HARGA_PER_SLOT_2TAHUN,
    }
    errors = []

    if request.method == 'POST':
        kode_toko        = request.POST.get('kode_toko', '').strip().lower()
        password_admin   = request.POST.get('password_admin', '')
        nama_pemilik     = request.POST.get('nama_pemilik', '').strip()
        email_owner      = request.POST.get('email_owner', '').strip().lower()
        password_owner   = request.POST.get('password_owner', '')
        phone            = request.POST.get('phone', '').strip()
        jumlah_slot      = max(1, int(request.POST.get('jumlah_slot', 1)))
        durasi           = request.POST.get('durasi', 'bulanan')

        # Validasi input dasar
        if not kode_toko:
            errors.append("Kode toko wajib diisi.")
        if not password_admin:
            errors.append("Password admin wajib diisi.")
        if not nama_pemilik:
            errors.append("Nama pemilik wajib diisi.")
        if not email_owner:
            errors.append("Email akun Korporasi wajib diisi.")
        elif User.objects.filter(email__iexact=email_owner).exists():
            errors.append(f"Email {email_owner} sudah terdaftar. Gunakan email lain untuk akun Korporasi.")
        if len(password_owner) < 6:
            errors.append("Password akun Korporasi minimal 6 karakter.")

        admin_user = None
        cabang_saya = None

        if not errors:
            # Verifikasi kepemilikan toko via kode toko
            admin_user = authenticate(request, username=f"{kode_toko}1", password=password_admin)
            if not admin_user:
                try:
                    cabang_cek = Cabang.objects.get(prefix=kode_toko)
                    admin_user = authenticate(request, username=cabang_cek.email, password=password_admin)
                except Cabang.DoesNotExist:
                    pass

            if not admin_user:
                errors.append("Kode toko atau password admin tidak sesuai.")
            else:
                try:
                    cabang_saya = admin_user.userprofile.cabang
                except Exception:
                    errors.append("Akun admin toko tidak memiliki toko terdaftar.")
                    admin_user = None

            if admin_user and cabang_saya and not errors:
                if cabang_saya.owner_id:
                    errors.append(f"Toko {cabang_saya.nama_toko} sudah terdaftar dalam Paket Korporasi.")
                # Email owner tidak boleh sama dengan email toko yang ada
                if email_owner == (cabang_saya.email or '').lower():
                    errors.append("Email Korporasi tidak boleh sama dengan email toko. Gunakan email berbeda.")

            if not errors:
                durasi_hari = {'bulanan': 30, '3bulanan': 90, '6bulanan': 180, 'tahunan': 365, '2tahunan': 730}
                hari = durasi_hari.get(durasi, 30)
                lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=hari)
                lisensi_grace   = lisensi_expired + datetime.timedelta(days=7)

                kuota_sisa = max(0, cabang_saya.kuota_transaksi)
                kuota_pool = jumlah_slot * KUOTA_PER_SLOT_BULANAN + kuota_sisa

                # Buat User BARU untuk akun Owner Korporasi (terpisah dari admin toko)
                owner_user = User()
                owner_user.username   = email_owner
                owner_user.email      = email_owner
                owner_user.first_name = nama_pemilik
                owner_user.is_active  = True
                owner_user.save()
                owner_user.set_password(password_owner)
                owner_user.save()

                owner = Owner.objects.create(
                    user=owner_user,
                    nama=nama_pemilik,
                    phone=phone,
                    jumlah_slot=jumlah_slot,
                    kuota_transaksi_pool=kuota_pool,
                    lisensi_expired=lisensi_expired,
                    lisensi_grace=lisensi_grace,
                )
                get_or_create_gudang(owner)

                cabang_saya.owner           = owner
                cabang_saya.paket           = None
                cabang_saya.lisensi_expired = None
                cabang_saya.lisensi_grace   = None
                cabang_saya.save()

                messages.success(request, (
                    f"Upgrade berhasil! Toko {cabang_saya.nama_toko} sudah berada di Paket Korporasi. "
                    f"Silakan login ke dashboard Korporasi menggunakan email: {email_owner}"
                ))
                return HttpResponseRedirect('/owner/login/')

    context = {
        'harga_info': harga_info,
        'kuota_per_slot': KUOTA_PER_SLOT_BULANAN,
        'errors': errors,
        'form': request.POST if request.method == 'POST' else {},
    }
    return render(request, 'owner/migrasi.html', context)

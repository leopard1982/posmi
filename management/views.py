from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
import datetime

from stock.models import DaftarPaket, Cabang, UserProfile
from promo.models import Promo, PromoUsed
from cms.models import Testimoni
from pos.models import Penjualan
from payment.models import TransaksiPembelian


def _require_superuser(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/')
    if not request.user.is_superuser:
        messages.error(request, "Halaman ini hanya untuk superadmin.")
        return HttpResponseRedirect('/')
    return None


def _nama_bulan(n):
    bulan = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
             'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    return bulan[n] if 1 <= n <= 12 else ''


def index(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    now  = datetime.datetime.now()
    today = now.date()

    # ── Stat cards ────────────────────────────────────────────────
    total_cabang    = Cabang.objects.count()
    cabang_aktif    = Cabang.objects.filter(is_active=True).count()
    total_paket     = DaftarPaket.objects.count()
    total_promo     = Promo.objects.filter(is_active=True).count()
    testimoni_pend  = Testimoni.objects.filter(is_verified=False).count()
    total_user      = User.objects.count()
    transaksi_bulan = Penjualan.objects.filter(
        is_paid=True, is_void=False,
        updated_at__month=now.month, updated_at__year=now.year
    ).count()

    # ── Pendapatan ─────────────────────────────────────────────────
    pendapatan_bulan = TransaksiPembelian.objects.filter(
        created_at__month=now.month, created_at__year=now.year
    ).aggregate(total=Sum('harga'))['total'] or 0

    pendapatan_hari = TransaksiPembelian.objects.filter(
        created_at__date=today
    ).aggregate(total=Sum('harga'))['total'] or 0

    # ── Grafik total pembelian per hari (30 hari terakhir) ──────────
    start_30 = today - datetime.timedelta(days=29)
    chart_harian_qs = (
        TransaksiPembelian.objects
        .filter(created_at__date__gte=start_30)
        .extra(select={'tgl': 'DATE(created_at)'})
        .values('tgl').annotate(total=Sum('harga')).order_by('tgl')
    )
    chart_hari_labels = [str(r['tgl']) for r in chart_harian_qs]
    chart_hari_data   = [r['total'] for r in chart_harian_qs]

    # ── Grafik total pembelian per bulan (12 bulan terakhir) ───────
    chart_bulan_labels, chart_bulan_data = [], []
    for i in range(11, -1, -1):
        tgt = now.month - i
        yr  = now.year + (tgt - 1) // 12
        mn  = ((tgt - 1) % 12) + 1
        total_bln = TransaksiPembelian.objects.filter(
            created_at__month=mn, created_at__year=yr
        ).aggregate(total=Sum('harga'))['total'] or 0
        chart_bulan_labels.append(_nama_bulan(mn))
        chart_bulan_data.append(total_bln)

    # ── Top 5 individual: pembelian bulan ini ──────────────────────
    top5_individual_bulan = (
        TransaksiPembelian.objects
        .filter(cabang__isnull=False, created_at__month=now.month, created_at__year=now.year)
        .values('cabang__nama_toko', 'cabang__prefix')
        .annotate(total=Sum('harga'))
        .order_by('-total')[:5]
    )

    # ── Top 5 korporasi: pembelian bulan ini ──────────────────────
    top5_korporasi_bulan = (
        TransaksiPembelian.objects
        .filter(owner__isnull=False, created_at__month=now.month, created_at__year=now.year)
        .values('owner__nama')
        .annotate(total=Sum('harga'))
        .order_by('-total')[:5]
    )

    # ── Top 5 individual: transaksi POS hari ini & bulan ini ───────
    top5_trx_individual_hari = (
        Penjualan.objects
        .filter(is_paid=True, is_void=False, updated_at__date=today)
        .values('cabang__nama_toko')
        .annotate(jml=Count('nota'))
        .order_by('-jml')[:5]
    )
    top5_trx_individual_bulan = (
        Penjualan.objects
        .filter(is_paid=True, is_void=False, updated_at__month=now.month, updated_at__year=now.year)
        .values('cabang__nama_toko')
        .annotate(jml=Count('nota'))
        .order_by('-jml')[:5]
    )

    # ── Top 5 korporasi: transaksi POS hari ini & bulan ini ────────
    top5_trx_korporasi_hari = (
        Penjualan.objects
        .filter(is_paid=True, is_void=False, updated_at__date=today, cabang__owner__isnull=False)
        .values('cabang__owner__nama')
        .annotate(jml=Count('nota'))
        .order_by('-jml')[:5]
    )
    top5_trx_korporasi_bulan = (
        Penjualan.objects
        .filter(is_paid=True, is_void=False, updated_at__month=now.month,
                updated_at__year=now.year, cabang__owner__isnull=False)
        .values('cabang__owner__nama')
        .annotate(jml=Count('nota'))
        .order_by('-jml')[:5]
    )

    # ── Daftar pelanggan individual ────────────────────────────────
    pelanggan_individual = (
        Cabang.objects
        .filter(owner__isnull=True)
        .annotate(total_pembelian=Sum('transaksi_pembelian__harga'))
        .order_by('-total_pembelian')[:20]
    )

    # ── Daftar pelanggan korporasi ─────────────────────────────────
    try:
        from owner.models import Owner
        pelanggan_korporasi = (
            Owner.objects
            .annotate(total_pembelian=Sum('transaksi_pembelian__harga'))
            .order_by('-total_pembelian')[:20]
        )
    except Exception:
        pelanggan_korporasi = []

    context = {
        'total_cabang': total_cabang, 'cabang_aktif': cabang_aktif,
        'total_paket': total_paket,   'total_promo': total_promo,
        'testimoni_pending': testimoni_pend, 'total_user': total_user,
        'transaksi_bulan': transaksi_bulan,
        'pendapatan_bulan': pendapatan_bulan, 'pendapatan_hari': pendapatan_hari,
        'bulan': _nama_bulan(now.month), 'tahun': now.year,
        'chart_hari_labels': chart_hari_labels, 'chart_hari_data': chart_hari_data,
        'chart_bulan_labels': chart_bulan_labels, 'chart_bulan_data': chart_bulan_data,
        'top5_individual_bulan': list(top5_individual_bulan),
        'top5_korporasi_bulan':  list(top5_korporasi_bulan),
        'top5_trx_individual_hari':  list(top5_trx_individual_hari),
        'top5_trx_individual_bulan': list(top5_trx_individual_bulan),
        'top5_trx_korporasi_hari':   list(top5_trx_korporasi_hari),
        'top5_trx_korporasi_bulan':  list(top5_trx_korporasi_bulan),
        'pelanggan_individual': pelanggan_individual,
        'pelanggan_korporasi':  pelanggan_korporasi,
    }
    return render(request, 'management/index.html', context)


# ─── DaftarPaket ──────────────────────────────────────────────────────────────

def paket_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        if aksi == 'tambah':
            p = DaftarPaket()
            p.nama = request.POST.get('nama', '')
            p.max_transaksi = int(request.POST.get('max_transaksi', 0))
            p.max_user_login = int(request.POST.get('max_user_login', 0))
            p.harga_per_bulan = int(request.POST.get('harga_per_bulan', 0))
            p.harga_per_tiga_bulan = int(request.POST.get('harga_per_tiga_bulan', 0))
            p.harga_per_enam_bulan = int(request.POST.get('harga_per_enam_bulan', 0))
            p.harga_per_tahun = int(request.POST.get('harga_per_tahun', 0))
            p.harga_per_dua_tahun = int(request.POST.get('harga_per_dua_tahun', 0))
            p.disc = int(request.POST.get('disc', 0))
            p.is_ceklist_barang = request.POST.get('is_ceklist_barang') == 'on'
            p.is_pembayaran_tempo = request.POST.get('is_pembayaran_tempo') == 'on'
            p.is_add_ons = request.POST.get('is_add_ons') == 'on'
            p.save()
            messages.success(request, f"Paket '{p.nama}' berhasil ditambahkan.")
        elif aksi == 'edit':
            p = get_object_or_404(DaftarPaket, pk=request.POST.get('paket_id'))
            p.nama = request.POST.get('nama', p.nama)
            p.max_transaksi = int(request.POST.get('max_transaksi', p.max_transaksi))
            p.max_user_login = int(request.POST.get('max_user_login', p.max_user_login))
            p.harga_per_bulan = int(request.POST.get('harga_per_bulan', p.harga_per_bulan))
            p.harga_per_tiga_bulan = int(request.POST.get('harga_per_tiga_bulan', p.harga_per_tiga_bulan))
            p.harga_per_enam_bulan = int(request.POST.get('harga_per_enam_bulan', p.harga_per_enam_bulan))
            p.harga_per_tahun = int(request.POST.get('harga_per_tahun', p.harga_per_tahun))
            p.harga_per_dua_tahun = int(request.POST.get('harga_per_dua_tahun', p.harga_per_dua_tahun))
            p.disc = int(request.POST.get('disc', p.disc))
            p.is_ceklist_barang = request.POST.get('is_ceklist_barang') == 'on'
            p.is_pembayaran_tempo = request.POST.get('is_pembayaran_tempo') == 'on'
            p.is_add_ons = request.POST.get('is_add_ons') == 'on'
            p.save()
            messages.success(request, f"Paket '{p.nama}' berhasil diperbarui.")
        elif aksi == 'hapus':
            p = get_object_or_404(DaftarPaket, pk=request.POST.get('paket_id'))
            nama = p.nama
            p.delete()
            messages.success(request, f"Paket '{nama}' berhasil dihapus.")
        return HttpResponseRedirect('/management/paket/')
    pakets = DaftarPaket.objects.all()
    return render(request, 'management/paket.html', {'pakets': pakets})


# ─── Pembelian ────────────────────────────────────────────────────────────────

def pembelian_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    from django.core.paginator import Paginator
    qs = TransaksiPembelian.objects.select_related('cabang', 'owner').order_by('-created_at')
    # Filter opsional
    tipe_filter = request.GET.get('tipe', '')
    q_filter    = request.GET.get('q', '')
    if tipe_filter:
        qs = qs.filter(tipe=tipe_filter)
    if q_filter:
        qs = qs.filter(
            Q(cabang__nama_toko__icontains=q_filter) |
            Q(owner__nama__icontains=q_filter) |
            Q(order_id__icontains=q_filter)
        )
    total_pendapatan = qs.aggregate(total=Sum('harga'))['total'] or 0
    paginator = Paginator(qs, 30)
    page_obj  = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'management/pembelian.html', {
        'page_obj': page_obj,
        'total_pendapatan': total_pendapatan,
        'tipe_filter': tipe_filter,
        'q_filter': q_filter,
        'tipe_choices': TransaksiPembelian.TIPE_CHOICES,
    })


# ─── Promo ────────────────────────────────────────────────────────────────────

def promo_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        if aksi == 'tambah':
            p = Promo()
            p.nama = request.POST.get('nama', '')
            p.kode = request.POST.get('kode', '').upper().strip()
            p.disc = int(request.POST.get('disc', 0))
            p.kuota = int(request.POST.get('kuota', 0))
            end = request.POST.get('end_period', '')
            p.end_period = end if end else None
            p.is_registrasi = request.POST.get('is_registrasi') == 'on'
            p.is_perpanjangan = request.POST.get('is_perpanjangan') == 'on'
            p.is_upgrade_lisensi = request.POST.get('is_upgrade_lisensi') == 'on'
            p.is_tambah_kuota = request.POST.get('is_tambah_kuota') == 'on'
            p.is_active = True
            p.save()
            messages.success(request, f"Promo '{p.nama}' berhasil ditambahkan.")
        elif aksi == 'edit':
            p = get_object_or_404(Promo, pk=request.POST.get('promo_id'))
            p.nama = request.POST.get('nama', p.nama)
            p.kode = request.POST.get('kode', p.kode).upper().strip()
            p.disc = int(request.POST.get('disc', p.disc))
            p.kuota = int(request.POST.get('kuota', p.kuota))
            end = request.POST.get('end_period', '')
            p.end_period = end if end else None
            p.is_registrasi = request.POST.get('is_registrasi') == 'on'
            p.is_perpanjangan = request.POST.get('is_perpanjangan') == 'on'
            p.is_upgrade_lisensi = request.POST.get('is_upgrade_lisensi') == 'on'
            p.is_tambah_kuota = request.POST.get('is_tambah_kuota') == 'on'
            p.save()
            messages.success(request, f"Promo '{p.nama}' berhasil diperbarui.")
        elif aksi == 'hapus':
            p = get_object_or_404(Promo, pk=request.POST.get('promo_id'))
            nama = p.nama
            p.delete()
            messages.success(request, f"Promo '{nama}' berhasil dihapus.")
        elif aksi == 'toggle':
            p = get_object_or_404(Promo, pk=request.POST.get('promo_id'))
            p.is_active = not p.is_active
            p.save()
            status = "diaktifkan" if p.is_active else "dinonaktifkan"
            messages.success(request, f"Promo '{p.nama}' berhasil {status}.")
        return HttpResponseRedirect('/management/promo/')
    promos = Promo.objects.annotate(terpakai=Count('promo_master')).order_by('-created_at')
    return render(request, 'management/promo.html', {'promos': promos})


# ─── Testimoni ────────────────────────────────────────────────────────────────

def testimoni_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        t = get_object_or_404(Testimoni, pk=request.POST.get('testimoni_id'))
        if aksi == 'approve':
            t.is_verified = True
            t.save()
            # Beri bonus Rp 50.000 wallet hanya untuk persetujuan pertama kali
            if not t.bonus_diberikan and t.cabang:
                from pos.models import DetailWalet
                BONUS_TESTIMONI = 50_000
                t.cabang.wallet += BONUS_TESTIMONI
                t.cabang.save(update_fields=['wallet'])
                DetailWalet.objects.create(
                    cabang=t.cabang,
                    keterangan='bonus_testimoni',
                    jumlah=BONUS_TESTIMONI,
                )
                t.bonus_diberikan = True
                t.save(update_fields=['bonus_diberikan'])
                messages.success(request, f"Testimoni disetujui. Bonus Rp 50.000 ditambahkan ke wallet toko {t.cabang.nama_toko}.")
            else:
                messages.success(request, "Testimoni berhasil disetujui.")
        elif aksi == 'reject':
            t.is_verified = False
            t.save()
            messages.success(request, "Testimoni berhasil ditolak.")
        elif aksi == 'hapus':
            t.delete()
            messages.success(request, "Testimoni berhasil dihapus.")
        return HttpResponseRedirect('/management/testimoni/')
    testimonis = Testimoni.objects.all().order_by('-created_at')
    return render(request, 'management/testimoni.html', {'testimonis': testimonis})


# ─── Cabang ───────────────────────────────────────────────────────────────────

def cabang_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        c = get_object_or_404(Cabang, pk=request.POST.get('cabang_id'))
        if aksi == 'toggle':
            c.is_active = not c.is_active
            c.save()
            status = "diaktifkan" if c.is_active else "dinonaktifkan"
            messages.success(request, f"Cabang '{c.nama_toko}' berhasil {status}.")
        elif aksi == 'set_paket':
            paket_id = request.POST.get('paket_id')
            if paket_id:
                paket = get_object_or_404(DaftarPaket, pk=paket_id)
                c.paket = paket
                c.kuota_transaksi = paket.max_transaksi
            else:
                c.paket = None
                c.lisensi_expired = None
                c.lisensi_grace = None
                c.kuota_transaksi = 75
            c.save()
            messages.success(request, f"Paket cabang '{c.nama_toko}' berhasil diperbarui.")
        elif aksi == 'set_lisensi':
            lisensi = request.POST.get('lisensi_expired', '')
            grace = request.POST.get('lisensi_grace', '')
            c.lisensi_expired = lisensi if lisensi else None
            c.lisensi_grace = grace if grace else None
            c.save()
            messages.success(request, f"Lisensi cabang '{c.nama_toko}' berhasil diperbarui.")
        return HttpResponseRedirect('/management/cabang/')
    cabangs = Cabang.objects.all().order_by('-created_at')
    pakets = DaftarPaket.objects.all()
    return render(request, 'management/cabang.html', {'cabangs': cabangs, 'pakets': pakets})


# ─── Users ────────────────────────────────────────────────────────────────────

def user_list(request):
    redirect = _require_superuser(request)
    if redirect:
        return redirect
    if request.method == 'POST':
        aksi = request.POST.get('aksi')
        u = get_object_or_404(User, pk=request.POST.get('user_id'))
        if aksi == 'reset_password':
            new_pass = request.POST.get('new_password', '')
            if new_pass:
                u.set_password(new_pass)
                u.save()
                messages.success(request, f"Password user '{u.username}' berhasil direset.")
        elif aksi == 'toggle_active':
            try:
                profile = u.userprofile
                profile.is_active = not profile.is_active
                profile.save()
                status = "diaktifkan" if profile.is_active else "dinonaktifkan"
                messages.success(request, f"User '{u.username}' berhasil {status}.")
            except Exception:
                messages.error(request, "User ini tidak memiliki profil.")
        return HttpResponseRedirect('/management/users/')
    users = User.objects.all().select_related('userprofile__cabang').order_by('-date_joined')
    return render(request, 'management/users.html', {'users': users})

from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.conf import settings
import midtransclient
from stock.models import DaftarPaket,prefixGenerator, Cabang, UserProfile, LogTransaksi
from django.contrib import messages
from django.contrib.auth.models import User
import datetime
from django.db.models import Q
from promo.views import cekKodeToko,cekKodeVoucher
from promo.models import Promo, PromoUsed
from pos.models import DetailWalet, Penjualan
from posmimail import posmiMail
from .models import GaransiRefund, PermintaanKonsultasi

REFUND_AUTO_LIMIT_TRANSAKSI = 50


def _sesuaikan_kasir_downgrade(cabang, max_kasir):
    """
    Saat downgrade, nonaktifkan kasir yang melebihi kuota paket baru.
    Kasir yang dipertahankan: urutan username terkecil (ter atas / paling lama).
    max_kasir=0 berarti unlimited — tidak ada yang dinonaktifkan.
    Mengembalikan list username kasir yang dinonaktifkan.
    """
    if max_kasir == 0:
        return []
    kasir_qs = (
        UserProfile.objects
        .filter(cabang=cabang, user__is_superuser=False)
        .select_related('user')
        .order_by('user__username')   # prefix1 < prefix2 < prefix3 ...
    )
    dinonaktifkan = []
    for idx, profile in enumerate(kasir_qs):
        if idx < max_kasir:
            # dalam kuota — pastikan aktif
            if not profile.is_active:
                profile.is_active = True
                profile.save(update_fields=['is_active'])
        else:
            # melebihi kuota — nonaktifkan
            if profile.is_active:
                profile.is_active = False
                profile.save(update_fields=['is_active'])
                dinonaktifkan.append(profile.user.username)
    return dinonaktifkan
PAKET_GRATIS_KUOTA_BULANAN = 75

def bayarAddon(request):
    """Proses pembayaran add-on: validasi → buat transaksi Midtrans → redirect ke halaman bayar."""
    import uuid as _uuid
    from payment.models import TokoAddon
    from django.http import HttpResponseRedirect as _Redir

    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = '/'

    if request.method != 'POST':
        return _Redir(asal)

    addon_type  = request.POST.get('addon_type', '').strip()
    kode_toko   = request.POST.get('kode_toko', '').strip().lower()
    email_owner = request.POST.get('email_owner', '').strip().lower()

    valid_types = [c[0] for c in TokoAddon.ADDON_CHOICES]
    if addon_type not in valid_types:
        messages.add_message(request, messages.SUCCESS, "Jenis add-on tidak valid.")
        return _Redir(asal)

    harga    = TokoAddon.HARGA.get(addon_type, 0)
    nama_adn = dict(TokoAddon.ADDON_CHOICES).get(addon_type, addon_type)

    # ── Jalur Individual ──
    if kode_toko:
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
        except Cabang.DoesNotExist:
            messages.add_message(request, messages.SUCCESS, f"Kode toko '{kode_toko}' tidak ditemukan.")
            return _Redir(asal)

        if cabang.paket is None and cabang.owner_id is None:
            messages.add_message(request, messages.SUCCESS,
                "Paket Gratis tidak dapat menggunakan add-on. Upgrade paket terlebih dahulu.")
            return _Redir(asal)

        if cabang.owner_id:
            messages.add_message(request, messages.SUCCESS,
                "Toko Korporasi: gunakan tab Korporasi dan masukkan email pemilik.")
            return _Redir(asal)

        expired_at = cabang.lisensi_expired
        TokoAddon.objects.get_or_create(
            cabang=cabang, addon_type=addon_type,
            defaults={'expired_at': expired_at, 'harga_dibayar': harga, 'status': TokoAddon.STATUS_NONAKTIF}
        )

        order_id   = _buat_order_id(f'ADN')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        from payment.models import PendingPayment
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_ADDON,
            data={'addon_type': addon_type, 'kode_toko': kode_toko},
            harga=harga,
        )
        try:
            redirect_url = prosesPayment(order_id, harga,
                nama_pembeli=cabang.nama_toko, email_pembeli=cabang.email or '',
                finish_url=finish_url)
            return _Redir(redirect_url)
        except Exception as ex:
            print(f"[bayarAddon] Midtrans error: {ex}")
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                "Gagal membuat transaksi pembayaran. Silakan coba beberapa saat lagi.")
            return _Redir(asal)

    # ── Jalur Korporasi ──
    if email_owner:
        try:
            from django.contrib.auth.models import User as _U
            owner = _U.objects.get(email__iexact=email_owner).owner_profile
        except Exception:
            messages.add_message(request, messages.SUCCESS,
                f"Email '{email_owner}' tidak ditemukan sebagai akun Korporasi.")
            return _Redir(asal)

        if not owner.is_active:
            messages.add_message(request, messages.SUCCESS,
                "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu.")
            return _Redir(asal)

        expired_at = owner.lisensi_expired
        TokoAddon.objects.get_or_create(
            owner=owner, addon_type=addon_type,
            defaults={'expired_at': expired_at, 'harga_dibayar': harga, 'status': TokoAddon.STATUS_NONAKTIF}
        )

        order_id   = _buat_order_id('ADN')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        from payment.models import PendingPayment
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_ADDON,
            data={'addon_type': addon_type, 'owner_id': str(owner.pk)},
            harga=harga,
        )
        try:
            redirect_url = prosesPayment(order_id, harga,
                nama_pembeli=owner.nama, email_pembeli=email_owner,
                finish_url=finish_url)
            return _Redir(redirect_url)
        except Exception as ex:
            print(f"[bayarAddon] Midtrans error: {ex}")
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                "Gagal membuat transaksi pembayaran. Silakan coba beberapa saat lagi.")
            return _Redir(asal)

    messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email owner Korporasi.")
    return _Redir(asal)


def requestAddon(request):
    """
    Permintaan aktivasi add-on dari landing page.
    - Individual (Bisnis Kecil/Medium): masukkan kode toko
    - Korporasi: masukkan email owner
    - Gratis: tidak bisa
    """
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal = "/"

    if request.method != 'POST':
        return HttpResponseRedirect(asal)

    addon_type  = request.POST.get('addon_type', '').strip()
    kode_toko   = request.POST.get('kode_toko', '').strip().lower()
    email_owner = request.POST.get('email_owner', '').strip().lower()

    from payment.models import TokoAddon
    # ── Trial Bundle: 3 hari untuk semua add-on ──
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
                messages.add_message(request, messages.SUCCESS, "Trial hanya untuk paket berbayar (Bisnis Kecil/Medium/Korporasi).")
                return HttpResponseRedirect(asal)
            if target_cabang.owner_id:
                target_owner = target_cabang.owner
                target_cabang = None
        elif email_owner:
            from django.contrib.auth.models import User as DjUser
            try:
                dj_user = DjUser.objects.get(email__iexact=email_owner)
                target_owner = dj_user.owner_profile
            except Exception:
                messages.add_message(request, messages.SUCCESS, f"Email '{email_owner}' tidak ditemukan.")
                return HttpResponseRedirect(asal)

        if not target_cabang and not target_owner:
            messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email Korporasi.")
            return HttpResponseRedirect(asal)

        from payment.models import TokoAddon
        import datetime as _dt
        trial_end = _dt.datetime.now() + _dt.timedelta(days=3)
        all_types = [TokoAddon.ADDON_BARCODE, TokoAddon.ADDON_NOTA, TokoAddon.ADDON_AKUNTING]
        activated = []
        for atype in all_types:
            kwargs = {'cabang': target_cabang} if target_cabang else {'owner': target_owner}
            kwargs['addon_type'] = atype
            existing = TokoAddon.objects.filter(**kwargs).first()
            if not existing:
                TokoAddon.objects.create(
                    **{k: v for k, v in kwargs.items()},
                    status=TokoAddon.STATUS_NONAKTIF,
                    expired_at=trial_end,
                    harga_dibayar=0,
                    catatan_admin='trial_3hari'
                )
                activated.append(atype)

        nama = (target_cabang.nama_toko if target_cabang else target_owner.nama)
        from posmimail import posmiMail
        posmiMail(
            "REQUEST TRIAL BUNDLE 3 HARI",
            f"{'Toko' if target_cabang else 'Owner Korporasi'}: {nama}\n"
            f"Trial bundle: {', '.join(all_types)}\nBerlaku 3 hari dari sekarang.\n\nAktifkan di Django Admin.",
            address="adhy.chandra@live.co.uk"
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan trial 3 hari untuk {nama} berhasil dikirim. Tim POSMI akan mengaktifkan setelah verifikasi.")
        return HttpResponseRedirect(asal)

    valid_types = [c[0] for c in TokoAddon.ADDON_CHOICES]
    if addon_type not in valid_types:
        messages.add_message(request, messages.SUCCESS, "Jenis add-on tidak valid.")
        return HttpResponseRedirect(asal)

    # ── Jalur Individual ──
    if kode_toko:
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
        except Cabang.DoesNotExist:
            messages.add_message(request, messages.SUCCESS, f"Kode toko '{kode_toko}' tidak ditemukan.")
            return HttpResponseRedirect(asal)

        # Validasi: tidak boleh gratis
        if cabang.paket is None and cabang.owner_id is None:
            messages.add_message(request, messages.SUCCESS,
                "Paket Gratis tidak dapat menggunakan add-on ini. Upgrade ke Bisnis Kecil atau Medium terlebih dahulu.")
            return HttpResponseRedirect(asal)

        # Korporasi harus lewat jalur email owner
        if cabang.owner_id:
            messages.add_message(request, messages.SUCCESS,
                "Toko Korporasi: gunakan email pemilik untuk mengaktifkan add-on.")
            return HttpResponseRedirect(asal)

        expired_at = cabang.lisensi_expired
        harga      = TokoAddon.HARGA.get(addon_type, 0)

        addon, created = TokoAddon.objects.get_or_create(
            cabang=cabang, addon_type=addon_type,
            defaults={'expired_at': expired_at, 'harga_dibayar': harga, 'status': TokoAddon.STATUS_NONAKTIF}
        )
        if not created:
            # Update expired_at jika berlangganan sudah diperpanjang
            addon.expired_at = expired_at
            addon.save(update_fields=['expired_at', 'updated_at'])

        # Kirim notifikasi ke admin POSMI
        from posmimail import posmiMail
        posmiMail(
            f"REQUEST ADD-ON: {addon.get_addon_type_display()}",
            f"Toko: {cabang.nama_toko} ({kode_toko})\n"
            f"Add-on: {addon.get_addon_type_display()}\n"
            f"Harga: Rp {harga:,}\n"
            f"Expired toko: {expired_at}\n\n"
            f"Aktifkan via Django Admin atau panel management.",
            address="adhy.chandra@live.co.uk"
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan add-on '{addon.get_addon_type_display()}' untuk toko {cabang.nama_toko} "
            f"berhasil dikirim. Tim POSMI akan menghubungi Anda setelah pembayaran dikonfirmasi.")
        return HttpResponseRedirect(asal)

    # ── Jalur Korporasi ──
    if email_owner:
        from django.contrib.auth.models import User as DjUser
        try:
            user = DjUser.objects.get(email__iexact=email_owner)
            owner = user.owner_profile
        except (DjUser.DoesNotExist, Exception):
            messages.add_message(request, messages.SUCCESS,
                f"Email pemilik Korporasi '{email_owner}' tidak ditemukan.")
            return HttpResponseRedirect(asal)

        if not owner.is_active:
            messages.add_message(request, messages.SUCCESS,
                "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu.")
            return HttpResponseRedirect(asal)

        harga    = TokoAddon.HARGA.get(addon_type, 0)
        expired_at = owner.lisensi_expired

        addon, created = TokoAddon.objects.get_or_create(
            owner=owner, addon_type=addon_type,
            defaults={'expired_at': expired_at, 'harga_dibayar': harga, 'status': TokoAddon.STATUS_NONAKTIF}
        )
        if not created:
            addon.expired_at = expired_at
            addon.save(update_fields=['expired_at', 'updated_at'])

        from posmimail import posmiMail
        posmiMail(
            f"REQUEST ADD-ON KORPORASI: {addon.get_addon_type_display()}",
            f"Owner: {owner.nama} ({email_owner})\n"
            f"Add-on: {addon.get_addon_type_display()}\n"
            f"Harga: Rp {harga:,}\n"
            f"Berlaku untuk semua toko Korporasi.\n\n"
            f"Aktifkan via Django Admin.",
            address="adhy.chandra@live.co.uk"
        )
        messages.add_message(request, messages.SUCCESS,
            f"Permintaan add-on '{addon.get_addon_type_display()}' untuk akun Korporasi {owner.nama} "
            f"berhasil dikirim. Tim POSMI akan menghubungi Anda setelah pembayaran dikonfirmasi.")
        return HttpResponseRedirect(asal)

    messages.add_message(request, messages.SUCCESS, "Masukkan kode toko atau email owner Korporasi.")
    return HttpResponseRedirect(asal)


def addonStatus(request):
    """Cek status toko + addon tertentu untuk validasi modal landing page."""
    from django.http import JsonResponse
    from payment.models import TokoAddon

    kode       = request.GET.get('kode', '').strip().lower()
    email      = request.GET.get('email', '').strip().lower()
    addon_type = request.GET.get('addon_type', '').strip()

    # ── Jalur kode toko ──
    if kode:
        try:
            cabang = Cabang.objects.get(prefix=kode)
        except Cabang.DoesNotExist:
            return JsonResponse({'ok': False, 'pesan': f"Kode toko '{kode}' tidak ditemukan."})

        if cabang.paket is None and cabang.owner_id is None:
            return JsonResponse({'ok': False, 'pesan': f"Toko '{cabang.nama_toko}' masih menggunakan Paket Gratis. Upgrade ke Bisnis Kecil/Medium untuk menggunakan add-on."})

        if cabang.owner_id:
            return JsonResponse({'ok': False, 'pesan': "Toko Korporasi: gunakan tab 'Korporasi' dan masukkan email pemilik."})

        # Cek addon spesifik
        if addon_type:
            existing = TokoAddon.objects.filter(cabang=cabang, addon_type=addon_type).first()
            if existing and existing.is_active:
                exp = existing.expired_at.strftime('%d/%m/%Y') if existing.expired_at else '-'
                return JsonResponse({
                    'ok': True,
                    'sudah_aktif': True,
                    'toko_nama': cabang.nama_toko,
                    'expired_at': exp,
                    'pesan': f"Toko '{cabang.nama_toko}' sudah berlangganan add-on ini hingga {exp}. Klik Langganan untuk memperpanjang.",
                })

        return JsonResponse({'ok': True, 'sudah_aktif': False, 'toko_nama': cabang.nama_toko,
                             'pesan': f"Toko '{cabang.nama_toko}' ditemukan. Paket: {cabang.paket.nama}."})

    # ── Jalur email korporasi ──
    if email:
        try:
            from django.contrib.auth.models import User as DjUser
            user = DjUser.objects.get(email__iexact=email)
            owner = user.owner_profile
        except Exception:
            return JsonResponse({'ok': False, 'pesan': f"Email '{email}' tidak ditemukan sebagai akun Korporasi."})

        if not owner.is_active:
            return JsonResponse({'ok': False, 'pesan': "Paket Korporasi tidak aktif. Perpanjang langganan terlebih dahulu."})

        if addon_type:
            existing = TokoAddon.objects.filter(owner=owner, addon_type=addon_type).first()
            if existing and existing.is_active:
                exp = existing.expired_at.strftime('%d/%m/%Y') if existing.expired_at else '-'
                return JsonResponse({
                    'ok': True, 'sudah_aktif': True, 'toko_nama': owner.nama,
                    'expired_at': exp,
                    'pesan': f"Akun Korporasi '{owner.nama}' sudah berlangganan add-on ini hingga {exp}.",
                })

        return JsonResponse({'ok': True, 'sudah_aktif': False, 'toko_nama': owner.nama,
                             'pesan': f"Akun Korporasi '{owner.nama}' ditemukan."})

    return JsonResponse({'ok': False, 'pesan': ''})


def get_jumlah_bulan_paket(pkt):
    if pkt == 1:
        return 3
    if pkt == 2:
        return 6
    if pkt == 3:
        return 12
    if pkt == 4:
        return 24
    return 1

def prosesPayment(noTransaksi, jumlah, nama_pembeli='', email_pembeli='', finish_url=''):
    midtrans_server = settings.MIDTRANS_SERVER
    midtrans_client = settings.MIDTRANS_CLIENT
    midtrans_production = settings.MIDTRANS_PRODUCTION
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
        is_production=midtrans_production,
        server_key=midtrans_server,
        client_key=midtrans_client,
    )
    transaksi = snap.create_transaction(params)
    return transaksi['redirect_url']

def paymentRequest(request):
    if request.method=="POST":
        paket=""
        harga=None
        kode_toko = prefixGenerator()
        jenis_paket =""
        tipe=None #sm=small, med=medium, tr=trial
        pkt=None #untuk paket, 0 bulanan, 1 3bulan, 2 6bulan, 3 tahunan, 4 2tahunan, 5 trial
        daftarpaket = None
        if 'bisnis_kecil' in request.POST:
            tipe="sm"
            paket="PAKET BISNIS KECIL"
            paketan = request.POST['bisnis_kecil']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
                jenis_paket=f"1 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')}"
                pkt=0
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
                jenis_paket=f"3 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=13)).strftime('%d-%m-%Y')}"
                pkt=1
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
                jenis_paket=f"6 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=26)).strftime('%d-%m-%Y')}"
                pkt=2
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
                jenis_paket=f"Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=52)).strftime('%d-%m-%Y')}"
                pkt=3
            else:
                harga = daftarpaket.harga_per_dua_tahun
                jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=104)).strftime('%d-%m-%Y')}"
                pkt=4
        elif 'bisnis_medium' in request.POST:
            paket="PAKET BISNIS MEDIUM"
            paketan = request.POST['bisnis_medium']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Medium")
            tipe="med"
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
                jenis_paket=f"1 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')}"
                pkt=0
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
                jenis_paket=f"3 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=13)).strftime('%d-%m-%Y')}"
                pkt=1
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
                jenis_paket=f"6 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=26)).strftime('%d-%m-%Y')}"
                pkt=2
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
                jenis_paket=f"Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=52)).strftime('%d-%m-%Y')}"
                pkt=3
            else:
                harga = daftarpaket.harga_per_dua_tahun
                jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=104)).strftime('%d-%m-%Y')}"
                pkt=4
        else:
            tipe="tr"
            pkt=0
            paket="PAKET DASAR"
            harga=0
            jenis_paket=f"Gratis selamanya dengan maksimal {PAKET_GRATIS_KUOTA_BULANAN} transaksi per bulan"

        pricing_options = []
        package_options = []
        if daftarpaket:
            pricing_options = [
                {
                    'pkt': 0,
                    'value': 'bulanan',
                    'label': 'Per Bulan',
                    'duration': '1 Bulan',
                    'harga': daftarpaket.harga_per_bulan,
                    'note': 'Cocok untuk mulai mencoba paket bisnis.',
                },
                {
                    'pkt': 1,
                    'value': '3bulanan',
                    'label': 'Per 3 Bulan',
                    'duration': '3 Bulan',
                    'harga': daftarpaket.harga_per_tiga_bulan,
                    'note': 'Lebih praktis untuk operasional kuartalan.',
                },
                {
                    'pkt': 2,
                    'value': '6bulanan',
                    'label': 'Per 6 Bulan',
                    'duration': '6 Bulan',
                    'harga': daftarpaket.harga_per_enam_bulan,
                    'note': 'Pilihan stabil untuk setengah tahun.',
                },
                {
                    'pkt': 3,
                    'value': 'tahunan',
                    'label': 'Per Tahun',
                    'duration': '1 Tahun',
                    'harga': daftarpaket.harga_per_tahun,
                    'note': 'Rekomendasi untuk penggunaan rutin.',
                },
                {
                    'pkt': 4,
                    'value': '2tahunan',
                    'label': 'Per 2 Tahun',
                    'duration': '2 Tahun',
                    'harga': daftarpaket.harga_per_dua_tahun,
                    'note': 'Paling tenang untuk jangka panjang.',
                },
            ]
            for option in [
                ('sm', 'Bisnis Kecil', 'Paket lincah untuk toko yang mulai berkembang.'),
                ('med', 'Bisnis Medium', 'Paket lebih lega untuk transaksi dan operasional lebih besar.'),
            ]:
                try:
                    paket_option = DaftarPaket.objects.get(nama=option[1])
                    package_options.append({
                        'tipe': option[0],
                        'nama': option[1],
                        'deskripsi': option[2],
                        'selected': tipe == option[0],
                        'max_transaksi': paket_option.max_transaksi,
                        'max_user_login': paket_option.max_user_login,
                        'harga_per_bulan': paket_option.harga_per_bulan,
                        'harga_per_tiga_bulan': paket_option.harga_per_tiga_bulan,
                        'harga_per_enam_bulan': paket_option.harga_per_enam_bulan,
                        'harga_per_tahun': paket_option.harga_per_tahun,
                        'harga_per_dua_tahun': paket_option.harga_per_dua_tahun,
                    })
                except DaftarPaket.DoesNotExist:
                    pass

        context = {
            'paket':paket,
            'harga':harga,
            'kode_toko':kode_toko,
            'jenis_paket':jenis_paket,
            'tipe':tipe,
            'pkt':pkt,
            'pricing_options': pricing_options,
            'package_options': package_options,
        }
        if (tipe == "tr"):
            return render(request,'registrasi/registrasi.html',context)
        else:
            return render(request,'registrasi/registrasi_bayar.html',context)
    return HttpResponseRedirect('/')

def requestDemoAplikasi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal = "/"

    if request.method != "POST":
        return HttpResponseRedirect('/')

    nama = request.POST.get('nama','').strip()
    email = request.POST.get('email','').strip().lower()
    aplikasi_demo = request.POST.get('aplikasi_demo','').strip()
    keterangan = request.POST.get('keterangan','').strip()
    pilihan_aplikasi = dict(PermintaanKonsultasi.PILIHAN_APLIKASI)

    if not nama or not email or aplikasi_demo not in pilihan_aplikasi:
        messages.add_message(request,messages.SUCCESS,"Permintaan demo belum lengkap. Silakan isi nama, email, dan aplikasi yang ingin didemokan.")
        return HttpResponseRedirect(asal)

    permintaan = PermintaanKonsultasi()
    permintaan.nama = nama
    permintaan.email = email
    permintaan.jenis_permintaan = 'demo_aplikasi'
    permintaan.aplikasi_demo = aplikasi_demo
    permintaan.keterangan = keterangan
    permintaan.save()

    nama_aplikasi = pilihan_aplikasi[aplikasi_demo]
    tanggal_request = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    message = f"Permintaan Demo Aplikasi Baru\n\nNama: {nama}\nEmail: {email}\nAplikasi: {nama_aplikasi}\nKeterangan: {keterangan or '-'}\nTanggal: {tanggal_request}\n\nSilakan tindak lanjuti permintaan demo ini."
    posmiMail("PERMINTAAN DEMO APLIKASI",message=message,address="adhy.chandra@live.co.uk")

    message_user = f"Halo {nama},\n\nTerima kasih sudah mengirimkan permintaan demo untuk {nama_aplikasi}. Tim POSMI sudah menerima data Sobat dan akan menghubungi melalui email ini.\n\nKeterangan:\n{keterangan or '-'}\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"
    posmiMail("Permintaan Demo Aplikasi Diterima",message=message_user,address=email)

    messages.add_message(request,messages.SUCCESS,"Permintaan demo aplikasi sudah terkirim. Terima kasih, kami akan segera menghubungi Sobat.")
    return HttpResponseRedirect(asal)

def paymentResponse(request):
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal="/"

    pkt=int(request.GET['pkt'])
    tipe=request.GET['tipe']
    jumlah_transaksi=0
    lisensi_grace=None
    lisensi_expired=None
    kode_referal = None
    harga = 0
    cabang_penerima = None

    print(pkt)
    if pkt==0:
        print('pkt0')
        if(tipe!="tr"):
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=30)
            lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
            if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_bulan
            elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_bulan
        else:
            lisensi_expired = None
            lisensi_grace = None
    elif pkt==1:
        print('pkt1')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=13)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_tiga_bulan
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_tiga_bulan
    elif pkt==2:
        print('pkt2')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=26)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_enam_bulan
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_enam_bulan
    elif pkt==3:
        print('pkt3')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=52)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_tahun
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_tahun
    elif pkt==4:
        print('pkt4')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=104)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_dua_tahun
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_dua_tahun
    if tipe=="tr":
        jumlah_transaksi=PAKET_GRATIS_KUOTA_BULANAN
        daftarpaket = None
    elif tipe=="sm":
        daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
        jumlah_transaksi=daftarpaket.max_transaksi
    elif tipe=="med":
        daftarpaket=DaftarPaket.objects.get(nama="Bisnis Medium")
        jumlah_transaksi=daftarpaket.max_transaksi

    

    if request.method=="POST":
        from payment.models import PendingPayment
        from django.contrib.auth.hashers import make_password as _mkpw

        try:
            voucher = str(request.POST.get('voucher', '')).lower()
            if voucher:
                cek_voucher = cekKodeVoucher(kode=voucher, tipe="reg")
            else:
                cek_voucher = {'status': False, 'disc': 0}
        except Exception:
            cek_voucher = {'status': False, 'disc': 0}

        if cek_voucher['status']:
            try:
                promo = Promo.objects.get(kode=voucher)
                harga = max(0, harga - promo.disc)
            except Exception:
                pass

        kode_toko    = request.POST.get('kode_toko', '')
        nama_toko    = request.POST.get('nama_toko', '')
        nama_cabang  = request.POST.get('nama_cabang', '')
        alamat_toko  = request.POST.get('alamat_toko', '')
        telpon_toko  = request.POST.get('telpon_toko', '')
        email_toko   = request.POST.get('email_toko', '')
        pemilik_toko = request.POST.get('pemilik_toko', '')
        password     = request.POST.get('password_admin', '')

        if Cabang.objects.filter(email=email_toko).exists():
            messages.add_message(request, messages.SUCCESS,
                'Pendaftaran Gagal: email sudah pernah terdaftar. Gunakan email lain.')
            return HttpResponseRedirect(asal)

        lisensi_days = 0
        if lisensi_expired:
            lisensi_days = (lisensi_expired - datetime.datetime.now()).days

        pending_data = {
            'tipe': tipe, 'pkt': pkt,
            'kode_toko': kode_toko, 'nama_toko': nama_toko, 'nama_cabang': nama_cabang,
            'alamat_toko': alamat_toko, 'telpon': telpon_toko,
            'email_toko': email_toko, 'pemilik_toko': pemilik_toko,
            'pw_hash': _mkpw(password),
            'voucher': request.POST.get('voucher', ''),
            'referensi': request.POST.get('referensi', ''),
            'lisensi_days': lisensi_days,
            'jumlah_transaksi': jumlah_transaksi,
        }

        # Paket gratis: proses langsung tanpa Midtrans
        if tipe == 'tr' or harga == 0:
            from payment.models import PendingPayment
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

        # Berbayar: simpan PendingPayment lalu redirect ke Midtrans
        order_id = _buat_order_id('REG')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"
        from payment.models import PendingPayment
        PendingPayment.objects.create(
            order_id=order_id,
            tipe=PendingPayment.TIPE_REGISTRASI,
            data=pending_data, harga=int(harga),
        )
        try:
            redirect_url = prosesPayment(order_id, int(harga),
                                         nama_pembeli=pemilik_toko, email_pembeli=email_toko,
                                         finish_url=finish_url)
            return HttpResponseRedirect(redirect_url)
        except Exception as ex:
            print(f'[paymentResponse] Midtrans error: {ex}')
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                'Gagal membuat transaksi pembayaran. Coba beberapa saat lagi.')
            return HttpResponseRedirect(asal)

    return HttpResponseRedirect(asal)

def ajukanRefundGaransi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal="/cms/"

    if not request.user.is_authenticated:
        messages.add_message(request,messages.SUCCESS,"Silakan login terlebih dahulu untuk mengajukan refund.")
        return HttpResponseRedirect('/login/')

    if not request.user.is_superuser:
        messages.add_message(request,messages.SUCCESS,"Hanya admin toko yang dapat mengajukan refund.")
        return HttpResponseRedirect(asal)

    if request.method!="POST":
        return HttpResponseRedirect(asal)

    try:
        cabang = request.user.userprofile.cabang
        garansi = GaransiRefund.objects.filter(cabang=cabang).order_by('-created_at').first()
        if garansi is None:
            messages.add_message(request,messages.SUCCESS,"Garansi refund belum tersedia untuk toko ini.")
            return HttpResponseRedirect(asal)

        if garansi.status != GaransiRefund.STATUS_ELIGIBLE:
            messages.add_message(request,messages.SUCCESS,"Pengajuan refund untuk pembelian ini sudah pernah dibuat.")
            return HttpResponseRedirect(asal)

        if datetime.datetime.now() > garansi.batas_pengajuan:
            garansi.status = GaransiRefund.STATUS_EXPIRED
            garansi.save()
            messages.add_message(request,messages.SUCCESS,"Masa pengajuan refund sudah melewati 30 hari sejak aktivasi.")
            return HttpResponseRedirect(asal)

        jumlah_transaksi = Penjualan.objects.filter(
            cabang=cabang,
            is_paid=True,
            is_void=False,
            created_at__gte=garansi.tanggal_aktivasi,
            created_at__lte=datetime.datetime.now(),
        ).count()

        garansi.alasan = request.POST.get('alasan','')
        garansi.jumlah_transaksi_saat_pengajuan = jumlah_transaksi
        garansi.requested_at = datetime.datetime.now()

        if jumlah_transaksi <= REFUND_AUTO_LIMIT_TRANSAKSI:
            garansi.status = GaransiRefund.STATUS_DIAJUKAN_AUTO
            garansi.alur_pengajuan = GaransiRefund.ALUR_AUTO
            pesan = "Pengajuan auto refund berhasil dikirim. Tim POSMI akan memvalidasi data pembayaran dan memproses pengembalian dana."
        else:
            garansi.status = GaransiRefund.STATUS_DIAJUKAN_MEDIASI
            garansi.alur_pengajuan = GaransiRefund.ALUR_MEDIASI
            pesan = "Pengajuan refund berhasil dikirim melalui jalur mediasi karena transaksi sudah lebih dari 15."

        garansi.save()
        messages.add_message(request,messages.SUCCESS,pesan)
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,"Pengajuan refund belum dapat diproses. Silakan coba kembali atau hubungi tim POSMI.")

    return HttpResponseRedirect(asal)

def getAdmin(kode_toko):
    try:
        user = User.objects.get(username=f"{kode_toko}1")
        userprofile = UserProfile.objects.get(user=user).nama_lengkap
        return userprofile
    except:
        return ""

def cekLisensi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"
    
    try:
        kode_toko = request.POST['id']
        tipe = request.GET['tipe']    
        info_registrasi=""
        list_kuota=[data for data in range(50,1500,50)]
        list_biaya = []
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
            if tipe=="small":
                info_registrasi="Perpanjangan Lisensi Bisnis Kecil"
            elif tipe=="medium":
                info_registrasi="Perpanjangan Lisensi Bisnis Kecil"
            elif tipe=="upgrade":
                if cabang.paket== None:
                    info_registrasi="Upgrade ke Paket Bisnis Kecil atau Medium"
                    daftarpaket = DaftarPaket.objects.all().filter(nama__in=['Bisnis Kecil','Bisnis Medium'])
                    sisa_uang=0
                    for daftar in daftarpaket:
                        data = {
                                "id":daftar.paket,
                                'nama':daftar.nama,
                            }
                        biaya_list=[]
                        if int(daftar.harga_per_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'bulanan',
                                'info': '1 bulanan',
                                'data':int(daftar.harga_per_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tiga_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tigabulanan',
                                'info':'3 bulanan',
                                'data':int(daftar.harga_per_tiga_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_enam_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'enambulanan',
                                'info':'6 bulanan',
                                'data':int(daftar.harga_per_enam_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tahunan',
                                'info':'1 tahunan',
                                'data':int(daftar.harga_per_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_dua_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'duatahunan',
                                'info':'2 tahunan',
                                'data':int(daftar.harga_per_dua_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        data['biaya']=biaya_list
                        list_biaya.append(data)
                    print(list_biaya)
                elif cabang.paket.nama=="Bisnis Kecil":
                    info_registrasi="Upgrade ke Paket Bisnis Medium"
                    daftarpaket = DaftarPaket.objects.all().filter(nama__in=['Bisnis Medium'])
                    sisa_hari = int((cabang.lisensi_expired-datetime.datetime.now()).days)
                    sisa_uang = 0
                    # cek apakah sisa hari masih bulanan?
                    sisa_uang = (cabang.paket.harga_per_tahun/365)*sisa_hari
                    for daftar in daftarpaket:
                        data = {
                                "id":str(daftar.paket),
                                'nama':daftar.nama,
                        }
                        
                        biaya_list=[]
                        if int(daftar.harga_per_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'bulanan',
                                'info': '1 bulanan',
                                'data':int(daftar.harga_per_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tiga_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tigabulanan',
                                'info':'3 bulanan',
                                'data':int(daftar.harga_per_tiga_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_enam_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'enambulanan',
                                'info':'6 bulanan',
                                'data':int(daftar.harga_per_enam_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tahunan',
                                'info':'1 tahunan',
                                'data':int(daftar.harga_per_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_dua_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'duatahunan',
                                'info':'2 tahunan',
                                'data':int(daftar.harga_per_dua_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        data['biaya']=biaya_list
                        print(data)
                        list_biaya.append(data)
                else:
                    messages.add_message(request,messages.SUCCESS,f"Paket untuk {cabang.nama_toko} sudah Medium tidak bisa melakukan upgrade. Yang bisa dilakukan adalah menambah kuota transaksi penjualan. Terima kasih.")
                    return HttpResponseRedirect('/')
            elif tipe=="kuota":
                info_registrasi="Penambahan Kuota"
            
            nama_admin = getAdmin(kode_toko)
            context = {
                'kode_toko':kode_toko,
                'cabang':cabang,
                'nama_admin':nama_admin,
                'info_registrasi':info_registrasi,
                'tipe':tipe,
                'list_kuota':list_kuota,
                'asal':asal,
                'list_biaya':list_biaya
            }
            return render(request,'registrasi/cek_lisensi.html',context)
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,"Kode Toko Tidak Ditemukan.")    
            if tipe=="small":
                return HttpResponseRedirect("/#lisensismall")
            elif tipe=="medium":
                return HttpResponseRedirect("/#lisensimedium")
            elif tipe=="upgrade":
                return HttpResponseRedirect("/#upgradepaket")
            elif tipe=="kuota":
                return HttpResponseRedirect("/#tambahkuota")
        
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,"Kode Toko Tidak Ditemukan.")
        return HttpResponseRedirect("/")
    
def hitungBiayaKuota(request):
    try:
        jumlah_kuota = int(request.GET['jumlah_kuota'])
        return HttpResponse(f'<span style="width:270px">Perkiraan Biaya adalah:</span> Rp.{int(jumlah_kuota*10000/50):,}.00')
    except:
        return HttpResponse('<span style="width:270px">Perkiraan Biaya adalah:</span> Rp.0.00')

def tambahKuota(request):
    from payment.models import PendingPayment
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

        # Potong wallet jika diminta
        gunakan_wallet = request.POST.get('gunakan_wallet') == 'on'
        wallet_dipakai = 0
        if gunakan_wallet and cabang.wallet > 0:
            wallet_dipakai = min(cabang.wallet, int(harga))
            harga = max(0, int(harga) - wallet_dipakai)

        # Jika wallet menutup penuh, proses langsung tanpa Midtrans
        if harga == 0 and wallet_dipakai > 0:
            from payment.models import PendingPayment
            from pos.models import DetailWalet
            order_id = _buat_order_id('KTQ')
            p = PendingPayment.objects.create(
                order_id=order_id, tipe=PendingPayment.TIPE_KUOTA,
                data={'kode_toko': kode_toko, 'jumlah_kuota': jumlah_kuota,
                      'voucher': voucher, 'referensi': cabang.kode_referal or ''},
                harga=0, status=PendingPayment.STATUS_PAID,
            )
            _proses_pending_payment(p)
            cabang.wallet -= wallet_dipakai
            cabang.save(update_fields=['wallet'])
            DetailWalet.objects.create(
                cabang=cabang, keterangan=f'potongan wallet tambah kuota {jumlah_kuota}',
                jumlah=wallet_dipakai,
            )
            messages.add_message(request, messages.SUCCESS,
                f'Berhasil! {jumlah_kuota} kuota ditambahkan. Wallet berkurang Rp {wallet_dipakai:,}.')
            return HttpResponseRedirect('/')

        order_id   = _buat_order_id('KTQ')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"

        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_KUOTA,
            data={'kode_toko': kode_toko, 'jumlah_kuota': jumlah_kuota,
                  'voucher': voucher, 'referensi': cabang.kode_referal or '',
                  'wallet_dipakai': wallet_dipakai},
            harga=int(harga),
        )
        try:
            user_adm = User.objects.get(username=f"{kode_toko}1")
            redirect_url = prosesPayment(
                order_id, int(harga),
                nama_pembeli=user_adm.first_name, email_pembeli=cabang.email or '',
                finish_url=finish_url,
            )
            return HttpResponseRedirect(redirect_url)
        except Exception as ex:
            print(f'[tambahKuota] Midtrans error: {ex}')
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                'Gagal membuat transaksi pembayaran. Coba beberapa saat lagi.')
            return HttpResponseRedirect(asal)
    except Exception as ex:
        print(ex)
        return HttpResponseRedirect(asal)
    
def hitungExpired(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"
    try:
        kode_toko = request.GET['id']
        cabang = Cabang.objects.get(prefix=kode_toko)
        metode = str(request.GET['list_biaya']).split('^')[0]
        if(metode==""):
            return HttpResponse("")
        tanggal_expired = None
        day=0
        if metode=="bulanan":
            day = 30
        elif metode=="tigabulanan":
            day = 30*3
        elif metode=="enambulanan":
            day = 30*6
        elif metode=="tahunan":
            day = 365
        elif metode=="duatahunan":
            day = 365*2
        
        try:
            sisa_hari = (cabang.lisensi_expired-datetime.datetime.now()).days
        except:
            sisa_hari=0
            day = day-sisa_hari
        try:
            if cabang.lisensi_expired< datetime.datetime.now():
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
            else:
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired = tanggal_expired + datetime.timedelta(days=day)
        except:
            tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        return HttpResponse(f"Lisensi akan berakhir: {tanggal_expired.strftime("%d/%m/%Y")}")
    except Exception as ex:
        print(ex)
        return HttpResponse("-")
    
def upgradeLisensi(request):
    from payment.models import PendingPayment
    try:
        asal = request.META['HTTP_REFERER']
    except Exception:
        asal = '/'

    try:
        kode_toko = request.GET['id']
        cabang    = Cabang.objects.get(prefix=kode_toko)
        paket_sebelumnya = cabang.paket
        metode = str(request.POST['list_biaya']).split('^')[0]
        paket_id = str(request.POST['list_biaya']).split('^')[1]
        paket = DaftarPaket.objects.get(paket=paket_id)
        if metode=="bulanan":
            day = 30
        elif metode=="tigabulanan":
            day = 30*3
        elif metode=="enambulanan":
            day = 30*6
        elif metode=="tahunan":
            day = 365
        elif metode=="duatahunan":
            day = 365*2

        try:
            sisa_hari = (cabang.lisensi_expired-datetime.datetime.now()).days
        except:
            sisa_hari=0
            day = day-sisa_hari

        try:
            if cabang.lisensi_expired< datetime.datetime.now():
                tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
            else:
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired = tanggal_expired + datetime.timedelta(days=day)
        except:
            tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        
        harga_map = {
            'bulanan': paket.harga_per_bulan, 'tigabulanan': paket.harga_per_tiga_bulan,
            'enambulanan': paket.harga_per_enam_bulan, 'tahunan': paket.harga_per_tahun,
            'duatahunan': paket.harga_per_dua_tahun,
        }
        harga = harga_map.get(metode, paket.harga_per_bulan)

        order_id   = _buat_order_id('UPG')
        finish_url = f"{request.scheme}://{request.get_host()}/payment/finish/?order_id={order_id}"

        day_map = {'bulanan':30,'tigabulanan':90,'enambulanan':180,'tahunan':365,'duatahunan':730}
        PendingPayment.objects.create(
            order_id=order_id, tipe=PendingPayment.TIPE_UPGRADE,
            data={'kode_toko': kode_toko, 'paket_id': str(paket.paket),
                  'metode': metode, 'day': day_map.get(metode, 30)},
            harga=int(harga),
        )
        try:
            user_adm = User.objects.get(username=f"{kode_toko}1")
            redirect_url = prosesPayment(
                order_id, int(harga),
                nama_pembeli=user_adm.first_name, email_pembeli=cabang.email or '',
                finish_url=finish_url,
            )
            return HttpResponseRedirect(redirect_url)
        except Exception as ex:
            print(f'[upgradeLisensi] Midtrans error: {ex}')
            PendingPayment.objects.filter(order_id=order_id).delete()
            messages.add_message(request, messages.SUCCESS,
                'Gagal membuat transaksi pembayaran. Coba beberapa saat lagi.')
            return HttpResponseRedirect(asal)
    except Exception as ex:
        print(ex)
        return HttpResponseRedirect(asal)


# ═══════════════════════════════════════════════════════════════════════════════
#  MIDTRANS UNIVERSAL PAYMENT LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def _buat_order_id(prefix):
    import uuid as _u
    return f"{prefix}-{_u.uuid4().hex[:10].upper()}"


def _proses_pending_payment(pending):
    """
    Eksekusi transaksi yang sudah dibayar berdasarkan tipe PendingPayment.
    Dipanggil oleh webhook notifikasi Midtrans.
    """
    from payment.models import PendingPayment, TokoAddon
    d = pending.data

    # ── REGISTRASI ──────────────────────────────────────────────────────────
    if pending.tipe == PendingPayment.TIPE_REGISTRASI:
        tipe          = d['tipe']
        pkt           = d['pkt']
        kode_toko     = d['kode_toko']
        nama_toko     = d['nama_toko']
        nama_cabang   = d['nama_cabang']
        alamat_toko   = d['alamat_toko']
        telpon        = d['telpon']
        email_toko    = d['email_toko']
        pemilik_toko  = d['pemilik_toko']
        pw_hash       = d['pw_hash']
        referensi     = d.get('referensi', '')
        voucher_kode  = d.get('voucher', '')
        lisensi_days  = d.get('lisensi_days', 0)
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
            paket=daftarpaket, nama_toko=nama_toko, nama_cabang=nama_cabang,
            alamat_toko=alamat_toko, telpon=telpon, email=email_toko,
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
        user.password = pw_hash
        user.save()

        from stock.models import UserProfile as UP
        UP.objects.create(user=user, cabang=cabang, nama_lengkap=pemilik_toko, is_active=True)

        posmiMail(
            "Terima Kasih Sudah Menggunakan POSMI",
            f"Halo Sobat {pemilik_toko}!\n\nAkun POSMI toko {nama_toko} sudah aktif.\n"
            f"Username: {kode_toko}1\nKode Toko: {kode_toko}\n\n"
            f"Login: https://posmi.pythonanywhere.com/login/",
            address=email_toko,
        )

    # ── UPGRADE / PERPANJANGAN LISENSI ──────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_UPGRADE:
        try:
            cabang = Cabang.objects.get(prefix=d['kode_toko'])
        except Cabang.DoesNotExist:
            return
        paket          = DaftarPaket.objects.get(paket=d['paket_id'])
        day            = d['day']
        paket_sebelumnya = cabang.paket

        try:
            if cabang.lisensi_expired and cabang.lisensi_expired > datetime.datetime.now():
                tanggal_expired = cabang.lisensi_expired + datetime.timedelta(days=day)
            else:
                tanggal_expired = datetime.datetime.now() + datetime.timedelta(days=day)
        except Exception:
            tanggal_expired = datetime.datetime.now() + datetime.timedelta(days=day)

        cabang.lisensi_expired = tanggal_expired
        cabang.lisensi_grace   = tanggal_expired + datetime.timedelta(days=7)
        cabang.kuota_transaksi = paket.max_transaksi if paket_sebelumnya is None else cabang.kuota_transaksi + paket.max_transaksi
        cabang.paket = paket
        cabang.save()

        if paket_sebelumnya is None and not GaransiRefund.objects.filter(cabang=cabang).exists():
            GaransiRefund.objects.create(
                cabang=cabang, paket=paket,
                jumlah_pembayaran=pending.harga, jumlah_bulan=1,
                tanggal_aktivasi=datetime.datetime.now(),
                batas_pengajuan=datetime.datetime.now() + datetime.timedelta(days=30),
            )

        _sesuaikan_kasir_downgrade(cabang, paket.max_user_login)

    # ── TAMBAH KUOTA ─────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_KUOTA:
        try:
            cabang = Cabang.objects.get(prefix=d['kode_toko'])
        except Cabang.DoesNotExist:
            return
        jumlah_kuota  = int(d['jumlah_kuota'])
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

        voucher_kode = d.get('voucher', '')
        if voucher_kode:
            try:
                promo = Promo.objects.get(kode=voucher_kode)
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

    # ── ADD-ON ───────────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_ADDON:
        addon_type = d['addon_type']
        if d.get('kode_toko'):
            try:
                cabang = Cabang.objects.get(prefix=d['kode_toko'])
                addon = TokoAddon.objects.filter(cabang=cabang, addon_type=addon_type).first()
                if addon:
                    addon.status     = TokoAddon.STATUS_AKTIF
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
                    addon.status     = TokoAddon.STATUS_AKTIF
                    addon.activated_at = datetime.datetime.now()
                    addon.expired_at   = owner.lisensi_expired
                    addon.harga_dibayar = pending.harga
                    addon.save()
            except Exception:
                pass

    # ── OWNER UPGRADE ────────────────────────────────────────────────────────
    elif pending.tipe == PendingPayment.TIPE_OWNER:
        try:
            from owner.models import Owner
            owner = Owner.objects.get(pk=d['owner_id'])
            day   = d['day']
            now   = datetime.datetime.now()
            if owner.lisensi_expired and owner.lisensi_expired > now:
                owner.lisensi_expired = owner.lisensi_expired + datetime.timedelta(days=day)
            else:
                owner.lisensi_expired = now + datetime.timedelta(days=day)
            owner.lisensi_grace = owner.lisensi_expired + datetime.timedelta(days=7)
            owner.save()
        except Exception:
            pass

    # ── Catat ke TransaksiPembelian ─────────────────────────────────────────
    try:
        from payment.models import TransaksiPembelian
        keterangan_map = {
            PendingPayment.TIPE_REGISTRASI: f"Registrasi toko {d.get('nama_toko','')}",
            PendingPayment.TIPE_UPGRADE:    f"Upgrade/Perpanjangan paket — {d.get('metode','')}",
            PendingPayment.TIPE_KUOTA:      f"Tambah kuota {d.get('jumlah_kuota','')} transaksi",
            PendingPayment.TIPE_ADDON:      f"Aktivasi add-on {d.get('addon_type','')}",
            PendingPayment.TIPE_OWNER:      f"Upgrade korporasi — {d.get('metode','')}",
        }
        cabang_obj = None
        owner_obj  = None
        if d.get('kode_toko'):
            cabang_obj = Cabang.objects.filter(prefix=d['kode_toko']).first()
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
    except Exception as _ex:
        print(f'[TransaksiPembelian] gagal catat: {_ex}')


def midtransNotifikasi(request):
    """
    Webhook server-to-server dari Midtrans.
    Aktifkan di Midtrans Dashboard → Settings → Payment → Notification URL.
    """
    import json, hashlib
    from django.views.decorators.csrf import csrf_exempt
    from payment.models import PendingPayment

    try:
        data       = json.loads(request.body)
        order_id   = data.get('order_id', '')
        trx_status = data.get('transaction_status', '')
        fraud      = data.get('fraud_status', 'accept')
        gross      = data.get('gross_amount', '0')

        # Verifikasi signature Midtrans
        raw  = f"{order_id}{trx_status}{gross}{settings.MIDTRANS_SERVER}"
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
    except Exception as ex:
        print(f'[midtransNotifikasi] error: {ex}')
        return HttpResponse('Error', status=500)

# ─── Tandai csrf_exempt di URL, bukan di sini ──────────────────────────────

def paymentFinish(request):
    """Halaman setelah user selesai bayar di Midtrans (redirect dari Midtrans)."""
    from payment.models import PendingPayment
    order_id = request.GET.get('order_id', '')
    status   = request.GET.get('transaction_status', 'pending')

    pending = None
    if order_id:
        pending = PendingPayment.objects.filter(order_id=order_id).first()

    paid = (pending and pending.status == PendingPayment.STATUS_PAID) or status in ('capture', 'settlement')
    context = {
        'paid':     paid,
        'order_id': order_id,
        'tipe':     pending.tipe if pending else '',
        'status':   status,
    }
    return render(request, 'payment/finish.html', context)


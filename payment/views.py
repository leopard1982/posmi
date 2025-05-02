from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.conf import settings
import midtransclient
from stock.models import DaftarPaket,prefixGenerator, Cabang, UserProfile
from django.contrib import messages
from django.contrib.auth.models import User


def prosesPayment(noTransaksi,jumlah):
    midtrans_server = settings.MIDTRANS_SERVER
    midtrans_client = settings.MIDTRANS_CLIENT
    midtrans_production = settings.MIDTRANS_PRODUCTION
    params = {
        'transaction_details': {
            'order_id':noTransaksi,
            'gross_amount':jumlah
        },
        'credit_card': {
            'secure':True
        }
    }
    snap = midtransclient.Snap(
        is_production=midtrans_production,
        server_key=midtrans_server,
        client_key=midtrans_client
    )

    transaksi = snap.create_transaction(params)
    return transaksi['redirect_url']

def paymentRequest(request):
    if request.method=="POST":
        paket=""
        harga=None
        kode_toko = prefixGenerator()
        if 'bisnis_kecil' in request.POST:
            paket="PAKET BISNIS KECIL"
            paketan = request.POST['bisnis_kecil']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
            else:
                harga = daftarpaket.harga_per_dua_tahun
        elif 'bisnis_medium' in request.POST:
            paket="PAKET BISNIS MEDIUM"
            paketan = request.POST['bisnis_medium']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Medium")
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
            else:
                harga = daftarpaket.harga_per_dua_tahun
        else:
            paket="PAKET DASAR"
            harga=0


        context = {
            'paket':paket,
            'harga':harga,
            'kode_toko':kode_toko
        }
        return render(request,'registrasi/registrasi.html',context)
    return HttpResponseRedirect('/')

def paymentResponse(request):
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal="/"

    if request.method=="POST":
        kode_toko = request.POST['kode_toko']
        nama_toko = request.POST['nama_toko']
        nama_cabang = request.POST['nama_cabang']
        alamat_toko = request.POST['alamat_toko']
        telpon_toko = request.POST['telpon_toko']
        email_toko = request.POST['email_toko']
        pemilik_toko = request.POST['pemilik_toko']
        password = request.POST['password_admin']

        try:
            cabang = Cabang.objects.get(email=email_toko)
            messages.add_message(request,messages.SUCCESS,'Pendaftaran Gagal, email sudah pernah teregistrasi. Silakan menggunakan email lain. Terima kasih.')
        except:
            cabang = Cabang()
            cabang.keterangan=""
            cabang.nama_toko=nama_toko
            cabang.nama_cabang=nama_cabang
            cabang.alamat_toko = alamat_toko
            cabang.telpon=telpon_toko
            cabang.email=email_toko
            cabang.prefix=kode_toko
            cabang.save()

            print(cabang)

            user = User()
            user.username=f"{kode_toko}1"
            user.email=email_toko
            user.first_name=pemilik_toko
            user.is_active=True
            user.is_superuser=True
            user.password=password
            user.save()
            user.set_password(password)
            user.save()

            userprofile = UserProfile()
            userprofile.user=user
            userprofile.cabang=cabang
            userprofile.nama_lengkap=pemilik_toko
            userprofile.save()

            messages.add_message(request,messages.SUCCESS,f"Selamat Untuk User Admin {kode_toko}1 berhasil dibuat. Silakan Login.")

    return HttpResponseRedirect(asal)


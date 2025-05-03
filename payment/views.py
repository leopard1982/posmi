from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.conf import settings
import midtransclient
from stock.models import DaftarPaket,prefixGenerator, Cabang, UserProfile
from django.contrib import messages
from django.contrib.auth.models import User
import datetime


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
        jenis_paket =""
        tipe=None #sm=small, med=medium, tr=trial
        pkt=None #untuk paket, 0 bulanan, 1 3bulan, 2 6bulan, 3 tahunan, 4 2tahunan, 5 trial
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
            jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(days=7)).strftime('%d-%m-%Y')}"


        context = {
            'paket':paket,
            'harga':harga,
            'kode_toko':kode_toko,
            'jenis_paket':jenis_paket,
            'tipe':tipe,
            'pkt':pkt
        }
        return render(request,'registrasi/registrasi.html',context)
    return HttpResponseRedirect('/')

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

    print(pkt)
    if pkt==0:
        print('pkt0')
        if(tipe!="tr"):
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=30)
            lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        else:
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=7)
            lisensi_grace = lisensi_expired
    elif pkt==1:
        print('pkt1')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=13)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
    elif pkt==2:
        print('pkt2')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=26)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
    elif pkt==3:
        print('pkt3')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=52)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
    elif pkt==4:
        print('pkt4')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=104)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)

    if tipe=="tr":
        jumlah_transaksi=100 #default jumlah transaksi adalah 100 kalau trial
    elif tipe=="sm":
        jumlah_transaksi=DaftarPaket.objects.get(nama="Bisnis Kecil").max_transaksi
    elif tipe=="med":
        jumlah_transaksi=DaftarPaket.objects.get(nama="Bisnis Medium").max_transaksi

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
            cabang.lisensi_expired=lisensi_expired
            cabang.lisensi_grace=lisensi_grace
            cabang.kuota_transaksi=jumlah_transaksi
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


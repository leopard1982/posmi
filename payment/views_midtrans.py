from django.http import HttpResponseRedirect
import midtransclient
import os
from django.conf import settings
from django.shortcuts import HttpResponse,render
from pos.models import DetailWalet
from promo.models import Promo, PromoUsed
from promo.views import cekKodeToko, cekKodeVoucher
from stock.models import Cabang, LogTransaksi, UserProfile
from posmimail import posmiMail
from django.contrib import messages
from payment.models import MidtransPayment
import datetime
from django.contrib.auth.models import User

def paymentMidtrans(order_id,jumlah):
    jumlah = jumlah
    snap = midtransclient.Snap(
        is_production=False,
        server_key=settings.MIDTRANS_SERVER,
        client_key=settings.MIDTRANS_CLIENT
    )

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": jumlah,
        },
        "credit_card": {
            "secure": True
        }
    }
    try:
        transaction = snap.create_transaction(parameters=param)
    except Exception as ex:
        print(ex)
        transaction = None
    return transaction

def bayarKuota(request,cabang:Cabang,voucher:str,walet:int,jumlah_kuota:int,harga:int):
    try:
        # update data voucher berkurang 1
        promo = Promo.objects.get(kode=voucher)
        promo.kuota -= 1
        promo.save()

        # simpan siapa pemakai voucher
        promoused = PromoUsed()
        promoused.cabang=cabang
        promoused.promo=promo
        promoused.save()
    except Exception as ex:
        print(f"error di update promo: {ex}")


    # simpan tambahan wallet untuk referal (kalau ada)
    try:
        print(f'penambahan wallet di cabang {cabang.nama_cabang} dengan kode referal {cabang.kode_referal}')
        kode_ref = cabang.kode_referal
        reff = Cabang.objects.get(prefix=kode_ref)
        reff.wallet = reff.wallet+walet
        reff.save()

        print('sekarang menambahkan detail wallet')
        detailwallet = DetailWalet()
        detailwallet.cabang=reff
        detailwallet.cabang_referensi=cabang
        detailwallet.jumlah=walet
        detailwallet.keterangan="penambahan kuota transaksi"
        detailwallet.save()
        print('detail wallet sudah ditambahkan')
    except Exception as ex:
        print(f"error di tambahan wallet: {ex}")

    jumlah_kuota = jumlah_kuota
    cabang.kuota_transaksi+=int(jumlah_kuota)
    cabang.save()

    try:
        user = request.user
        userprofile = UserProfile.objects.get(user=user)
        message = f"Halo Sobat {userprofile.nama_lengkap}!\n\nTerima kasih atas pembelian {int(jumlah_kuota):,} kuota transaksi dengan pembayaran sebesar: Rp.{int(harga):,} pada tanggal: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"
    except:
        # berarti user belum melakukan login
        message = f"Halo Sobat!\n\nTerima kasih atas pembelian {int(jumlah_kuota):,} kuota transaksi dengan pembayaran sebesar: Rp.{int(harga):,} pada tanggal: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"

    

    

    posmiMail("Terima Kasih Sudah Menggunakan POSMI",message=message,address=cabang.email)

    logtransaksi = LogTransaksi()
    logtransaksi.cabang=cabang
    logtransaksi.keterangan=f"pembelian kuota {jumlah_kuota}"
    logtransaksi.transaksi="kuota transaksi"
    logtransaksi.save()

    messages.add_message(request,messages.SUCCESS,f"Selamat kuota transaksi untuk toko {cabang.nama_toko} ({cabang.nama_cabang}) telah bertambah {jumlah_kuota} menjadi sebanyak: {cabang.kuota_transaksi} transaksi. ")


def bayarRegistrasi(request,midtranspayment:MidtransPayment):
    try:
        referensi_cek = cekKodeToko(str(midtranspayment.kode_referensi).lower())
    except:
        referensi_cek = False

    try:
        voucher = str(midtranspayment.kode_voucher).lower()
        if voucher!="":
            cek_voucher = cekKodeVoucher(kode=voucher,tipe="add")
        else:
            cek_voucher = {
                'status':False,
                'disc':0
            }
    except:
        cek_voucher = {
            'status':False,
            'disc':0
        }

    if(cek_voucher['status']):
        try:
            promo = Promo.objects.get(kode=midtranspayment.kode_voucher).lower()
            harga -= promo.disc
            promo.kuota-=1
            promo.save()
        except:
            pass

        
    if(referensi_cek):
        try:
            # simpan tambahan dana ke wallet
            cabang_penerima = Cabang.objects.get(prefix=str(midtranspayment.kode_referensi).lower())
            cabang_penerima.wallet = cabang_penerima.wallet +  int(harga*5/100)
            cabang_penerima.save(force_update=True)
        except:
            pass

    

    try:
        cabang = Cabang.objects.get(email=midtranspayment.email_toko)
        messages.add_message(request,messages.SUCCESS,'Pendaftaran Gagal, email sudah pernah teregistrasi. Silakan menggunakan email lain. Terima kasih.')
    except:
        cabang = Cabang()
        cabang.keterangan=""
        cabang.paket=midtranspayment.daftar_paket
        cabang.nama_toko=midtranspayment.nama_toko
        cabang.nama_cabang=midtranspayment.nama_cabang
        cabang.alamat_toko = midtranspayment.alamat_toko
        cabang.telpon=midtranspayment.telpon_toko
        cabang.email=midtranspayment.email_toko
        cabang.prefix=midtranspayment.kode_toko
        cabang.lisensi_expired=midtranspayment.lisensi_expired
        cabang.lisensi_grace=midtranspayment.lisensi_grace
        cabang.kuota_transaksi=midtranspayment.jml_kuota
        try:
            cabang.kode_referal = str(midtranspayment.kode_referensi).lower()
        except:
            pass
        cabang.no_nota=1
        cabang.save()

        if 'voucher' in request.POST:
            if cek_voucher['status']:
                promoused = PromoUsed()
                promoused.promo=promo
                promoused.cabang=cabang
                promoused.save()

            detailwallet = DetailWalet()
            detailwallet.cabang=cabang_penerima
            detailwallet.cabang_referensi=cabang
            detailwallet.jumlah=midtranspayment.referal_point
            detailwallet.keterangan="registrasi toko"
            detailwallet.save()

        print(cabang)

        user = User()
        user.username=f"{midtranspayment.kode_toko}1"
        user.email=midtranspayment.email_toko
        user.first_name=midtranspayment.pemilik_toko
        user.is_active=True
        user.is_superuser=True
        user.password=midtranspayment.password
        user.save()
        user.set_password(midtranspayment.password)
        user.save()

        userprofile = UserProfile()
        userprofile.user=user
        userprofile.cabang=cabang
        userprofile.nama_lengkap=midtranspayment.pemilik_toko
        userprofile.is_active=True
        userprofile.save()

        message = f"Halo Sobat {midtranspayment.pemilik_toko}!\n\nSelamat bergabung di aplikasi posmi. Informasi toko sobat adalah sebagai berikut:\nNama Toko: {midtranspayment.nama_toko}\nNama Cabang: {cabang}\nAlamat Toko: {midtranspayment.alamat_toko}\nKode Toko: {midtranspayment.kode_toko}\nEmail Toko: {midtranspayment.email_toko}\n\nUntuk user administrator bisa login menggunakan user {user} atau menggunakan email {midtranspayment.email_toko}. Password yang telah dibuat adalah [{midtranspayment.password}] dan harap disimpan baik-baik atau diganti secara berkala.\n\nUntuk login bisa melakukan akses ke: https://posmi.pythonanywhere.com/login/ \n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"

        posmiMail("Terima Kasih Sudah Menggunakan POSMI",message=message,address=midtranspayment.email_toko)

        messages.add_message(request,messages.SUCCESS,f"Selamat Untuk User Admin {midtranspayment.kode_toko}1 berhasil dibuat. Silakan Login.")



def responseMidtransPayment(request):
    order_id = request.GET['order_id']
    status = int(request.GET['status_code'])
    # <QueryDict: {'order_id': ['6cfdf066-f26d-40d3-8f91-d1ee47b4a6c8'], 'status_code': ['200'], 'transaction_status': ['capture']}>
    if status==200:
        midtranspayment = MidtransPayment.objects.get(id=order_id)
        
        if midtranspayment.transaksi=="kuota":
            # isikan ke bayarKuota
            bayarKuota(request,midtranspayment.cabang,midtranspayment.kode_voucher,midtranspayment.referal_point,midtranspayment.jml_kuota,midtranspayment.total)
            return HttpResponseRedirect('/')
        elif midtranspayment.transaksi=="registrasi":
            bayarRegistrasi(request,midtranspayment)
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Pembayaran POSMI gagal, silakan ulangi kembali...")
        return HttpResponseRedirect('/')
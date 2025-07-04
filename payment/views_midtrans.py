from django.http import HttpResponseRedirect
import midtransclient
import os
from django.conf import settings
from django.shortcuts import HttpResponse,render
from pos.models import DetailWalet
from promo.models import Promo, PromoUsed
from stock.models import Cabang, LogTransaksi, UserProfile
from posmimail import posmiMail
from django.contrib import messages
from payment.models import MidtransPayment
import datetime

def paymentMidtrans(order_id):
    jumlah = 200000
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

        user = request.user
        userprofile = UserProfile.objects.get(user=user)

        message = f"Halo Sobat {userprofile.nama_lengkap}!\n\nTerima kasih atas pembelian {int(jumlah_kuota):,} kuota transaksi dengan pembayaran sebesar: Rp.{int(harga):,} pada tanggal: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"

        posmiMail("Terima Kasih Sudah Menggunakan POSMI",message=message,address=cabang.email)

        logtransaksi = LogTransaksi()
        logtransaksi.cabang=cabang
        logtransaksi.keterangan=f"pembelian kuota {jumlah_kuota}"
        logtransaksi.transaksi="kuota transaksi"
        logtransaksi.save()

                
        messages.add_message(request,messages.SUCCESS,f"Selamat kuota transaksi untuk toko {cabang.nama_toko} ({cabang.nama_cabang}) telah bertambah {jumlah_kuota} menjadi sebanyak: {cabang.kuota_transaksi} transaksi. ")
        return HttpResponseRedirect('/')

def responseMidtransPayment(request):
    order_id = request.GET['order_id']
    status = int(request.GET['status_code'])
    # <QueryDict: {'order_id': ['6cfdf066-f26d-40d3-8f91-d1ee47b4a6c8'], 'status_code': ['200'], 'transaction_status': ['capture']}>
    if status==200:
        midtranspayment = MidtransPayment.objects.get(id=order_id)
        
        if midtranspayment.transaksi=="kuota":
            # isikan ke bayarKuota
            bayarKuota(request,midtranspayment.cabang,midtranspayment.kode_voucher,midtranspayment.referal_point,midtranspayment.jml_kuota,midtranspayment.total)
    else:
        messages.add_message(request,messages.SUCCESS,"Pembayaran POSMI gagal, silakan ulangi kembali...")
        return HttpResponseRedirect('/')
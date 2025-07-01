from stock.models import Cabang,DaftarPaket

def updateKuota():
    cabang = Cabang.objects.all()

    for cab in cabang:
        try:
            cab.kuota_transaksi = cab.paket.max_transaksi
            cab.no_nota=1
            cab.save()
        except:
            pass
    print('ok, max transaksi sudah diupdate')
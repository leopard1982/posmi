from stock.models import Cabang,DaftarPaket
import os
from django.conf import settings

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

def delHistoryDownload():
    base_dir = settings.BASE_DIR
    listfile = os.listdir(os.path.join(base_dir,'download_history'))
    for file in listfile:
        os.remove(os.path.join(base_dir,f'download_history/{file}'))
    print('finish')
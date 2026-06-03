from stock.models import Cabang,DaftarPaket
from owner.models import Owner, KUOTA_PER_SLOT_BULANAN

PAKET_GRATIS_KUOTA_BULANAN = 75

def updateKuota():
    # Reset kuota per cabang (individual & gratis)
    for cab in Cabang.objects.filter(owner__isnull=True):
        try:
            if cab.paket:
                cab.kuota_transaksi = cab.paket.max_transaksi
            else:
                cab.kuota_transaksi = PAKET_GRATIS_KUOTA_BULANAN
            cab.no_nota = 1
            cab.save()
        except:
            pass

    # Reset pool Korporasi
    for own in Owner.objects.all():
        try:
            own.kuota_transaksi_pool = own.jumlah_slot * KUOTA_PER_SLOT_BULANAN
            own.save()
        except:
            pass

    print('ok, max transaksi sudah diupdate')

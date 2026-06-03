from django.urls import path
from .views import index,hapusItems,tambahItems,ubahItems,tambahBarang,loginkan,logoutkan,hapusTransaksi
from .views import bayarTransaksi,printTransaksi,gantiStatusOpen,updateBarangSatuan, reprintTransaksi
from .views import printKuitansi, lupaPassword, resetPassword, riwayatSaya, cetakRekap, printCekTransaksi, printTempoTransaksi

urlpatterns = [
    path('', index,name='index_pos'),
    path('hapus_item/',hapusItems,name="hapus_items"),
    path('hapus/',hapusTransaksi,name="hapus_transaksi"),
    path('tambah/',tambahItems,name="tambah_items"),
    path('ubah/',ubahItems,name='ubah_items'),
    path('tambah2/',tambahBarang,name='tambah_barang_pos'),
    path('login/',loginkan,name="loginkan"),
    path('logout/',logoutkan,name='logoutkan'),
    path('bayar/',bayarTransaksi,name="bayar_transaksi"),
    path('print/<str:nota>/',printTransaksi,name="print_transaksi"),
    path('print/re/<str:nota>/',reprintTransaksi,name="reprint_transaksi"),
    path('print/kuitansi/<str:nota>/',printKuitansi,name="print_kuitansi"),
    path('cek/<str:nota>/',printCekTransaksi,name="print_cek_transaksi"),
    path('print/tempo/<str:nota>/',printTempoTransaksi,name="print_tempo_transaksi"),
    path('status/',gantiStatusOpen,name="ganti_status_open"),
    path('harga/update/',updateBarangSatuan,name='update_barang_satuan'),
    path('lupa-password/',lupaPassword,name="lupa_password"),
    path('reset-password/<uuid:token>/',resetPassword,name="reset_password"),
    path('riwayat/',riwayatSaya,name="riwayat_saya"),
    path('riwayat/cetak/',cetakRekap,name="cetak_rekap"),
]

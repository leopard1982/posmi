from django.urls import path
from .views import index, infoToko, daftarBarang, transaksiBulanBerjalan,transaksiBulanLain

urlpatterns = [
    path('', index,name='index_cms'),
    path('toko/info/',infoToko,name="info_toko"),
    path('barang/daftar/',daftarBarang,name='daftar_barang'),
    path('history/bb/',transaksiBulanBerjalan,name='transaksi_bulan_berjalan'),
    path('history/bl/',transaksiBulanLain,name='transaksi_bulan_lain')
]

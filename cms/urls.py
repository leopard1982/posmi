from django.urls import path
from .views import index, infoToko, daftarBarang, transaksiBulanBerjalan,transaksiBulanLain,profilSaya
from .views import editBarang

urlpatterns = [
    path('', index,name='index_cms'),
    path('toko/info/',infoToko,name="info_toko"),
    path('barang/daftar/',daftarBarang,name='daftar_barang'),
    path('barang/edit/',editBarang,name="edit_barang"),
    path('history/bb/',transaksiBulanBerjalan,name='transaksi_bulan_berjalan'),
    path('history/bl/',transaksiBulanLain,name='transaksi_bulan_lain'),
    path('profil/',profilSaya,name="profil_saya")
]

from django.urls import path
from .views import index, infoToko, daftarBarang, transaksiBulanBerjalan,transaksiBulanLain,profilSaya
from .views import editBarang, tambahBarang,downloadTemplate,konfirmasiUpload, hapusBarang, downloadBarang
from .views import viewLog,daftarKasir,tambahKasir

urlpatterns = [
    path('', index,name='index_cms'),
    path('toko/info/',infoToko,name="info_toko"),
    path('barang/daftar/',daftarBarang,name='daftar_barang'),
    path('barang/edit/',editBarang,name="edit_barang"),
    path('history/bb/',transaksiBulanBerjalan,name='transaksi_bulan_berjalan'),
    path('history/bl/',transaksiBulanLain,name='transaksi_bulan_lain'),
    path('profil/',profilSaya,name="profil_saya"),
    path('barang/tambah/',tambahBarang,name="tambah_barang"),
    path('barang/template/',downloadTemplate,name="download_template"),
    path('barang/upload/',konfirmasiUpload,name='konfirmasi_upload'),
    path('barang/hapus/',hapusBarang,name="hapus_barang"),
    path('barang/download/',downloadBarang,name='download_barang'),
    path('log/',viewLog,name="view_log"),
    path('kasir/',daftarKasir,name="daftar_kasir"),
    path('kasir/tambah/',tambahKasir,name="tambah_kasir")
]

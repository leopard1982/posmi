from django.urls import path
from .views import index, infoToko, daftarBarang, transaksiBulanBerjalan,transaksiBulanLain,profilSaya
from .views import editBarang, tambahBarang,downloadTemplate,konfirmasiUpload, hapusBarang, downloadBarang
from .views import viewLog,daftarKasir,tambahKasir,detailPenjualan,konfirmasiVoid,tidakVoid,okeVoid
from .views import gantiEmail,konfirmasiEmail,tambahKuotaAdmin,upgradePaketAdmin,gantiPassword,updateStatusKasir
from .views import detailPengguna,updateFoto,updatePassword,updateNama

urlpatterns = [
    path('', index,name='index_cms'),
    path('toko/info/',infoToko,name="info_toko"),
    path('barang/daftar/',daftarBarang,name='daftar_barang'),
    path('barang/edit/',editBarang,name="edit_barang"),
    path('history/bb/',transaksiBulanBerjalan,name='transaksi_bulan_berjalan'),
    path('history/bl/',transaksiBulanLain,name='transaksi_bulan_lain'),
    path('history/detail/',detailPenjualan,name='detail_penjualan_histori'),
    path('profil/',profilSaya,name="profil_saya"),
    path('barang/tambah/',tambahBarang,name="tambah_barang"),
    path('barang/template/',downloadTemplate,name="download_template"),
    path('barang/upload/',konfirmasiUpload,name='konfirmasi_upload'),
    path('barang/hapus/',hapusBarang,name="hapus_barang"),
    path('barang/download/',downloadBarang,name='download_barang'),
    path('log/',viewLog,name="view_log"),
    path('kasir/',daftarKasir,name="daftar_kasir"),
    path('kasir/tambah/',tambahKasir,name="tambah_kasir"),
    path('void/',konfirmasiVoid,name='konfirmasi_void'),
    path('void/tidak/',tidakVoid,name="tidak_void"),
    path('void/ok/',okeVoid,name="oke_void"),
    path('email/',gantiEmail,name="ganti_email"),
    path('<str:id>/',konfirmasiEmail,name="konfirmasi_email"),
    path('kuota/<str:id>/',tambahKuotaAdmin,name="tambah_kuota_admin"),
    path('paket/<str:id>/',upgradePaketAdmin,name="upgrade_paket_admin"),
    path('pass/change/',gantiPassword,name="ganti_password"),
    path('kasir/status/',updateStatusKasir,name='update_status_kasir'),
    path('user/detail/',detailPengguna,name="detail_pengguna"),
    path('user/foto/',updateFoto,name="update_foto"),
    path('user/pass/',updatePassword,name="update_password"),
    path('user/nama/',updateNama,name="update_nama"),
]

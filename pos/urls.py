from django.urls import path
from .views import index,kurangiItems,tambahItems,ubahItems,tambahBarang,loginkan,logoutkan,hapusTransaksi

urlpatterns = [
    path('', index,name='index_pos'),
    path('kurang/',kurangiItems,name="kurangi_items"),
    path('hapus/',hapusTransaksi,name="hapus_transaksi"),
    path('tambah/',tambahItems,name="tambah_items"),
    path('ubah/',ubahItems,name='ubah_items'),
    path('tambah2/',tambahBarang,name='tambah_barang'),
    path('login/',loginkan,name="loginkan"),
    path('logout/',logoutkan,name='logoutkan')
]

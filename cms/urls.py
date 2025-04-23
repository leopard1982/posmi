from django.urls import path
from .views import index, infoToko, daftarBarang

urlpatterns = [
    path('', index,name='index_cms'),
    path('toko/info/',infoToko,name="info_toko"),
    path('barang/daftar/',daftarBarang,name='daftar_barang')
]

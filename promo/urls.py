from django.urls import path
from .views import getPromo, requestKodeVoucher,requestKodeToko

urlpatterns = [
    path('',getPromo,name="get_promo"),
    path('voucher/check/',requestKodeVoucher,name="request_kode_voucher"),
    path('toko/check/',requestKodeToko,name='request_kode_toko')
]

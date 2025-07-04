from django.urls import path
from .views import paymentRequest, paymentResponse, cekLisensi,hitungBiayaKuota,tambahKuota,hitungExpired
from .views import upgradeLisensi,hitungPanjangLisensi,perpanjangLisensi
from .views_midtrans import responseMidtransPayment

urlpatterns = [
    path('req/',paymentRequest,name='payment_request' ),
    path('res/',paymentResponse,name='payment_response'),
    path('lisensi/',cekLisensi,name="cek_lisensi"),
    path('lisensi/perpanjangan/',hitungPanjangLisensi,name="hitung_panjang_lisensi"),
    path('lisensi/perpanjangan/ok/',perpanjangLisensi,name="perpanjang_lisensi"),
    path('lisensi/kuota/hitung/',hitungBiayaKuota,name="hitung_biaya_kuota"),
    path('lisensi/kuota/tambah/',tambahKuota,name="tambah_kuota"),
    path('lisensi/upgrade/hitung/',hitungExpired,name="hitung_expired"),
    path('lisensi/upgrade/',upgradeLisensi,name="upgrade_lisensi"),
    path('response/',responseMidtransPayment,name='response_midtrans_payment')
]

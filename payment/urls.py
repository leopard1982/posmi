from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import paymentRequest, paymentResponse, cekLisensi, hitungBiayaKuota, tambahKuota, hitungExpired
from .views import upgradeLisensi
from .views import ajukanRefundGaransi, requestDemoAplikasi
from .views import requestAddon, addonStatus, bayarAddon
from .views import midtransNotifikasi, paymentFinish

urlpatterns = [
    path('req/',  paymentRequest,        name='payment_request'),
    path('demo/', requestDemoAplikasi,   name='request_demo_aplikasi'),
    path('res/',  paymentResponse,       name='payment_response'),
    path('finish/', paymentFinish,       name='payment_finish'),
    path('notif/', csrf_exempt(midtransNotifikasi), name='midtrans_notifikasi'),
    path('refund/ajukan/', ajukanRefundGaransi, name='ajukan_refund_garansi'),
    path('lisensi/', cekLisensi,         name='cek_lisensi'),
    path('lisensi/kuota/hitung/', hitungBiayaKuota, name='hitung_biaya_kuota'),
    path('lisensi/kuota/tambah/', tambahKuota,      name='tambah_kuota'),
    path('lisensi/upgrade/hitung/', hitungExpired,  name='hitung_expired'),
    path('lisensi/upgrade/', upgradeLisensi,        name='upgrade_lisensi'),
    # Add-ons
    path('addon/request/', requestAddon, name='request_addon'),
    path('addon/bayar/',   bayarAddon,   name='bayar_addon'),
    path('addon/status/',  addonStatus,  name='addon_status'),
]

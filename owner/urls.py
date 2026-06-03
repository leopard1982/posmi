from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='owner_dashboard'),
    path('register/', views.registerOwner, name='owner_register'),
    path('login/', views.loginOwner, name='owner_login'),
    path('klaim/', views.klaimToko, name='owner_klaim_toko'),
    path('lepas/<int:cabang_id>/', views.lepasToko, name='owner_lepas_toko'),
    path('masuk/<int:cabang_id>/', views.masukToko, name='owner_masuk_toko'),
    path('keluar/', views.keluarToko, name='owner_keluar_toko'),
    path('upgrade/', views.upgradePaketOwner, name='owner_upgrade_paket'),
    path('migrasi/', views.migrasiKeKorporasi, name='owner_migrasi'),
    path('downgrade/', views.downgradeKorporasi, name='owner_downgrade'),
    path('transfer/', views.requestTransfer, name='owner_request_transfer'),
    path('transfer/approval/', views.approvalTransfer, name='owner_approval_transfer'),
    path('transfer/barang/<int:cabang_id>/', views.ajaxBarangCabang, name='owner_ajax_barang'),
    # Master Barang Korporasi
    path('barang/', views.barangIndex, name='owner_barang_index'),
    path('barang/<int:cabang_id>/', views.barangToko, name='owner_barang_toko'),
    path('barang/<int:cabang_id>/tambah/', views.tambahBarangOwner, name='owner_barang_tambah'),
    path('barang/<int:cabang_id>/edit/<int:barang_id>/', views.editBarangOwner, name='owner_barang_edit'),
    path('barang/<int:cabang_id>/upload/', views.uploadBarangOwner, name='owner_barang_upload'),
    path('barang/<int:cabang_id>/upload/konfirmasi/', views.konfirmasiUploadOwner, name='owner_barang_konfirmasi'),
    path('barang/<int:cabang_id>/download/', views.downloadBarangOwner, name='owner_barang_download'),
    path('barang/template/', views.downloadTemplateOwner, name='owner_barang_template'),
    # Gudang Utama
    path('gudang/', views.gudangView, name='owner_gudang'),
    path('gudang/distribusi/', views.distribusiGudangKeToko, name='owner_distribusi_gudang'),
    path('gudang/tambah/', views.tambahBarangOwner, name='owner_gudang_tambah'),
    path('gudang/upload/', views.uploadBarangOwner, name='owner_gudang_upload'),
    path('gudang/upload/konfirmasi/', views.konfirmasiUploadOwner, name='owner_gudang_konfirmasi'),
    path('gudang/download/', views.downloadBarangOwner, name='owner_gudang_download'),
    path('gudang/edit/<int:barang_id>/', views.editBarangOwner, name='owner_gudang_edit'),
    path('barang/<int:cabang_id>/stok/', views.barangToko, name='owner_stok_toko'),
    # Distribusi (halaman terpisah)
    path('distribusi/', views.distribusiView, name='owner_distribusi'),
    # Order dari Toko
    path('order-toko/', views.orderTokoView, name='owner_order_toko'),
    # Pengiriman Gudang
    path('gudang/kirim/', views.buatPengiriman, name='owner_buat_pengiriman'),
    path('gudang/pengiriman/', views.daftarPengiriman, name='owner_daftar_pengiriman'),
    path('gudang/pengiriman/<int:pengiriman_id>/', views.detailPengiriman, name='owner_detail_pengiriman'),
    path('gudang/monitoring/', views.monitoringStokToko, name='owner_monitoring_stok'),
    path('gudang/request-barang/', views.approvalMasterBarang, name='owner_approval_master_barang'),
    # Manajemen Toko
    path('toko/', views.manajemenToko, name='owner_manajemen_toko'),
]

from django.urls import path
from .views import index, infoToko, daftarBarang, transaksiBulanBerjalan,transaksiBulanLain,profilSaya
from .views import editBarang, tambahBarang,downloadTemplate,konfirmasiUpload, hapusBarang, downloadBarang
from .views import viewLog,daftarKasir,tambahKasir,detailPenjualan,konfirmasiVoid,tidakVoid,okeVoid
from .views import gantiEmail,konfirmasiEmail,tambahKuotaAdmin,upgradePaketAdmin,gantiPassword,updateStatusKasir
from .views import detailPengguna,updateFoto,updatePassword,updateNama, tambahBarangSatuan
from .views import masterPaket, masterPromo, masterTestimoni, masterCabang, verifikasiEmail, kirimUlangVerifikasi
from .views import transferStokCMS, daftarBarangKorporasi, penerimaanBarang, konfirmasiItemPenerimaan, orderBarang, downloadTemplateOrder, requestMasterBarang, laporanStokBarang, downloadLaporanStok, cmsAddonStatus, cmsAddonAktifkan, cmsAddonSettings, cmsCetakBarcode, cmsCetakBarcodePage, cmsLaporanAkunting, cmsLaporanAkuntingPreview, cmsLaporanAkuntingExcel, cmsLaporanAkuntingCetak, cetakRekapCMS
from .views import daftarTempoTransaksi, bayarTempoTransaksi, printLunasTempo

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
    path('barang/add/',tambahBarangSatuan,name='tambah_barang_satuan'),
    path('log/',viewLog,name="view_log"),
    path('kasir/',daftarKasir,name="daftar_kasir"),
    path('kasir/tambah/',tambahKasir,name="tambah_kasir"),
    path('void/',konfirmasiVoid,name='konfirmasi_void'),
    path('void/tidak/',tidakVoid,name="tidak_void"),
    path('void/ok/',okeVoid,name="oke_void"),
    path('email/',gantiEmail,name="ganti_email"),
    path('pass/change/',gantiPassword,name="ganti_password"),
    path('kasir/status/',updateStatusKasir,name='update_status_kasir'),
    path('user/detail/',detailPengguna,name="detail_pengguna"),
    path('user/foto/',updateFoto,name="update_foto"),
    path('user/pass/',updatePassword,name="update_password"),
    path('user/nama/',updateNama,name="update_nama"),
    # Master data (superuser only)
    path('master/paket/',masterPaket,name="master_paket"),
    path('master/promo/',masterPromo,name="master_promo"),
    path('master/testimoni/',masterTestimoni,name="master_testimoni"),
    path('master/cabang/',masterCabang,name="master_cabang"),
    # Korporasi
    path('transfer/', transferStokCMS, name='transfer_stok_cms'),
    path('barang/korporasi/', daftarBarangKorporasi, name='daftar_barang_korporasi'),
    path('penerimaan/', penerimaanBarang, name='penerimaan_barang'),
    path('penerimaan/<int:pengiriman_id>/', konfirmasiItemPenerimaan, name='konfirmasi_penerimaan'),
    path('order/', orderBarang, name='order_barang_cms'),
    path('request-barang/', requestMasterBarang, name='request_master_barang'),
    path('order/template/', downloadTemplateOrder, name='download_template_order'),
    path('addons/', cmsAddonStatus, name='cms_addon_status'),
    path('addons/<str:addon_type>/', cmsAddonAktifkan, name='cms_addon_aktifkan'),
    path('addons/<str:addon_type>/settings/', cmsAddonSettings, name='cms_addon_settings'),
    path('cetak-barcode/', cmsCetakBarcodePage, name='cms_cetak_barcode_page'),
    path('laporan-akunting/', cmsLaporanAkunting, name='cms_laporan_akunting'),
    path('laporan-akunting/preview/', cmsLaporanAkuntingPreview, name='cms_laporan_akunting_preview'),
    path('laporan-akunting/excel/', cmsLaporanAkuntingExcel, name='cms_laporan_akunting_excel'),
    path('laporan-akunting/cetak/', cmsLaporanAkuntingCetak, name='cms_laporan_akunting_cetak'),
    path('barang/<int:barang_id>/barcode/', cmsCetakBarcode, name='cms_cetak_barcode'),
    path('tempo/', daftarTempoTransaksi, name='daftar_tempo_transaksi'),
    path('tempo/bayar/', bayarTempoTransaksi, name='bayar_tempo_transaksi'),
    path('tempo/print/', printLunasTempo, name='print_lunas_tempo'),
    path('transaksi/download/', cetakRekapCMS, name='cetak_rekap_cms'),
    path('stok/laporan/', laporanStokBarang, name='laporan_stok_barang'),
    path('stok/laporan/download/', downloadLaporanStok, name='download_laporan_stok'),
    path('verifikasi-email/<uuid:token>/', verifikasiEmail, name='verifikasi_email'),
    path('verifikasi-email/kirim-ulang/', kirimUlangVerifikasi, name='kirim_ulang_verifikasi'),
    # Wildcard harus di paling bawah
    path('kuota/<str:id>/',tambahKuotaAdmin,name="tambah_kuota_admin"),
    path('paket/<str:id>/',upgradePaketAdmin,name="upgrade_paket_admin"),
    path('<str:id>/',konfirmasiEmail,name="konfirmasi_email"),
]

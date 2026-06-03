from django.contrib import admin
from stock.models import DaftarPaket,Pembayaran
from .models import GaransiRefund, PermintaanKonsultasi
# Register your models here.

admin.site.register(DaftarPaket)
admin.site.register(Pembayaran)

@admin.register(PermintaanKonsultasi)
class PermintaanKonsultasiAdmin(admin.ModelAdmin):
    list_display = ('nama','email','jenis_permintaan','aplikasi_demo','created_at')
    list_filter = ('jenis_permintaan','aplikasi_demo','created_at')
    search_fields = ('nama','email','keterangan')

@admin.register(GaransiRefund)
class GaransiRefundAdmin(admin.ModelAdmin):
    list_display = ('cabang','paket','jumlah_pembayaran','status','alur_pengajuan','jumlah_transaksi_saat_pengajuan','batas_pengajuan','requested_at')
    list_filter = ('status','alur_pengajuan','paket','created_at','requested_at')
    search_fields = ('cabang__nama_toko','cabang__nama_cabang','cabang__email','alasan','catatan_admin')
    readonly_fields = ('created_at','updated_at')

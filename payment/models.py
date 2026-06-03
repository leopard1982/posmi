import datetime

from django.contrib.auth.models import User
from django.db import models
from stock.models import Cabang, DaftarPaket


class TokoAddon(models.Model):
    """Add-on berbayar per toko atau per owner Korporasi."""

    ADDON_BARCODE   = 'barcode'
    ADDON_NOTA      = 'nota_custom'
    ADDON_AKUNTING  = 'akunting'
    ADDON_CHOICES   = [
        (ADDON_BARCODE,  'Cetak Label Barcode'),
        (ADDON_NOTA,     'Custom Template Nota'),
        (ADDON_AKUNTING, 'Laporan Akunting Otomatis'),
    ]
    HARGA = {
        ADDON_BARCODE:  50_000,
        ADDON_NOTA:     75_000,
        ADDON_AKUNTING: 100_000,
    }

    STATUS_AKTIF    = 'aktif'
    STATUS_NONAKTIF = 'nonaktif'   # belum/tidak diaktifkan
    STATUS_EXPIRED  = 'expired'    # masa aktif habis, fitur dimatikan
    STATUS_CHOICES  = [
        (STATUS_AKTIF,    'Aktif'),
        (STATUS_NONAKTIF, 'Tidak Aktif'),
        (STATUS_EXPIRED,  'Expired'),
    ]

    # Satu dari dua: individual atau korporasi
    cabang        = models.ForeignKey(Cabang, on_delete=models.CASCADE, null=True, blank=True, related_name='addons')
    owner         = models.ForeignKey('owner.Owner', on_delete=models.CASCADE, null=True, blank=True, related_name='addons')
    addon_type    = models.CharField(max_length=20, choices=ADDON_CHOICES)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_NONAKTIF)
    activated_at  = models.DateTimeField(null=True, blank=True)
    expired_at    = models.DateTimeField(null=True, blank=True)  # = lisensi_expired toko/owner
    harga_dibayar = models.PositiveIntegerField(default=0)
    catatan_admin = models.CharField(max_length=200, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ('cabang', 'addon_type'),
            ('owner', 'addon_type'),
        ]

    def __str__(self):
        target = self.cabang.nama_toko if self.cabang_id else (self.owner.nama if self.owner_id else '-')
        return f"{target} — {self.get_addon_type_display()} [{self.status}]"

    @property
    def is_active(self):
        if self.status != self.STATUS_AKTIF:
            return False
        if self.expired_at and datetime.datetime.now() > self.expired_at.replace(tzinfo=None):
            return False
        return True

    @classmethod
    def get_for_cabang(cls, cabang, addon_type):
        """Kembalikan addon aktif untuk toko (individual atau via owner)."""
        # Coba individual dulu
        try:
            a = cls.objects.get(cabang=cabang, addon_type=addon_type)
            return a if a.is_active else None
        except cls.DoesNotExist:
            pass
        # Coba owner korporasi
        if cabang.owner_id:
            try:
                a = cls.objects.get(owner=cabang.owner, addon_type=addon_type)
                return a if a.is_active else None
            except cls.DoesNotExist:
                pass
        return None

# Create your models here.
class AddonConfig(models.Model):
    """Konfigurasi pengaturan per add-on per toko."""

    cabang     = models.ForeignKey(Cabang, on_delete=models.CASCADE, related_name='addon_configs')
    addon_type = models.CharField(max_length=20, choices=TokoAddon.ADDON_CHOICES)
    config     = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('cabang', 'addon_type')]

    def __str__(self):
        return f"{self.cabang.nama_toko} — {self.addon_type}"

    def get(self, key, default=None):
        return self.config.get(key, default)


class PendingPayment(models.Model):
    """Menyimpan data transaksi sementara sebelum pembayaran Midtrans dikonfirmasi."""

    TIPE_REGISTRASI = 'registrasi'
    TIPE_UPGRADE    = 'upgrade'
    TIPE_KUOTA      = 'kuota'
    TIPE_ADDON      = 'addon'
    TIPE_OWNER      = 'owner_upgrade'

    STATUS_PENDING  = 'pending'
    STATUS_PAID     = 'paid'
    STATUS_FAILED   = 'failed'
    STATUS_EXPIRED  = 'expired'

    order_id   = models.CharField(max_length=120, unique=True)
    tipe       = models.CharField(max_length=20)
    data       = models.JSONField(default=dict)
    harga      = models.PositiveIntegerField(default=0)
    status     = models.CharField(max_length=10, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_id} [{self.tipe}] {self.status}"


class TransaksiPembelian(models.Model):
    """Rekam setiap pembayaran yang berhasil dikonfirmasi Midtrans."""
    TIPE_REGISTRASI = 'registrasi'
    TIPE_UPGRADE    = 'upgrade'
    TIPE_KUOTA      = 'kuota'
    TIPE_ADDON      = 'addon'
    TIPE_OWNER      = 'owner_upgrade'
    TIPE_CHOICES    = [
        (TIPE_REGISTRASI, 'Registrasi Paket'),
        (TIPE_UPGRADE,    'Upgrade/Perpanjangan Lisensi'),
        (TIPE_KUOTA,      'Tambah Kuota Transaksi'),
        (TIPE_ADDON,      'Aktivasi Add-on'),
        (TIPE_OWNER,      'Upgrade Korporasi'),
    ]

    cabang     = models.ForeignKey(Cabang, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaksi_pembelian')
    owner      = models.ForeignKey('owner.Owner', on_delete=models.SET_NULL, null=True, blank=True, related_name='transaksi_pembelian')
    order_id   = models.CharField(max_length=120, unique=True)
    tipe       = models.CharField(max_length=20, choices=TIPE_CHOICES)
    keterangan = models.CharField(max_length=200, blank=True)
    harga      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.cabang.nama_toko if self.cabang_id else (str(self.owner) if self.owner_id else '-')
        return f"{target} | {self.get_tipe_display()} | Rp {self.harga:,}"


class TokoGetToko(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="referal")
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,related_name='paketnya')
    registrar = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang_baru",blank=True,null=True)
    nilai = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_withdraw = models.BooleanField(default=True)

class PermintaanKonsultasi(models.Model):
    PILIHAN_JENIS = [
        ('konsultasi_gratis','Konsultasi Gratis'),
        ('demo_aplikasi','Demo Aplikasi'),
    ]

    PILIHAN_APLIKASI = [
        ('jurnal_koperasi','Aplikasi Jurnal untuk Koperasi'),
        ('pos','Aplikasi Penjualan (POS)'),
        ('platform_baca','Aplikasi Platform Baca'),
    ]

    nama = models.CharField(max_length=100)
    email = models.EmailField(max_length=200)
    jenis_permintaan = models.CharField(max_length=50,choices=PILIHAN_JENIS,default='konsultasi_gratis')
    aplikasi_demo = models.CharField(max_length=50,choices=PILIHAN_APLIKASI,blank=True,null=True)
    keterangan = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama} - {self.get_jenis_permintaan_display()}"

class GaransiRefund(models.Model):
    STATUS_ELIGIBLE = 'eligible'
    STATUS_DIAJUKAN_AUTO = 'diajukan_auto'
    STATUS_DIAJUKAN_MEDIASI = 'diajukan_mediasi'
    STATUS_DISETUJUI = 'disetujui'
    STATUS_DITOLAK = 'ditolak'
    STATUS_DIBAYAR = 'dibayar'
    STATUS_EXPIRED = 'expired'

    PILIHAN_STATUS = [
        (STATUS_ELIGIBLE, 'Belum diajukan'),
        (STATUS_DIAJUKAN_AUTO, 'Diajukan auto refund'),
        (STATUS_DIAJUKAN_MEDIASI, 'Diajukan mediasi'),
        (STATUS_DISETUJUI, 'Disetujui'),
        (STATUS_DITOLAK, 'Ditolak'),
        (STATUS_DIBAYAR, 'Sudah dibayar'),
        (STATUS_EXPIRED, 'Masa garansi berakhir'),
    ]

    ALUR_AUTO = 'auto_refund'
    ALUR_MEDIASI = 'mediasi'

    PILIHAN_ALUR = [
        (ALUR_AUTO, 'Auto refund'),
        (ALUR_MEDIASI, 'Mediasi'),
    ]

    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name='garansi_refund')
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,related_name='garansi_refund_paket',blank=True,null=True)
    jumlah_pembayaran = models.PositiveIntegerField(default=0)
    jumlah_bulan = models.PositiveIntegerField(default=1)
    tanggal_aktivasi = models.DateTimeField()
    batas_pengajuan = models.DateTimeField()
    status = models.CharField(max_length=30,choices=PILIHAN_STATUS,default=STATUS_ELIGIBLE)
    alur_pengajuan = models.CharField(max_length=30,choices=PILIHAN_ALUR,blank=True,null=True)
    alasan = models.TextField(blank=True,null=True)
    jumlah_transaksi_saat_pengajuan = models.PositiveIntegerField(default=0)
    requested_at = models.DateTimeField(blank=True,null=True)
    processed_at = models.DateTimeField(blank=True,null=True)
    processed_by = models.ForeignKey(User,on_delete=models.RESTRICT,blank=True,null=True,related_name='refund_diproses')
    catatan_admin = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def masih_bisa_diajukan(self):
        return self.status == self.STATUS_ELIGIBLE and datetime.datetime.now() <= self.batas_pengajuan

    @property
    def sisa_hari(self):
        sisa = (self.batas_pengajuan - datetime.datetime.now()).days
        return max(sisa, 0)

    def __str__(self):
        return f"{self.cabang} - {self.get_status_display()}"

    def save(self,*args,**kwargs):
        super(GaransiRefund,self).save(*args,**kwargs)
        if self.status == self.STATUS_DIBAYAR:
            Cabang.objects.filter(pk=self.cabang_id).update(
                paket=None,
                lisensi_expired=None,
                lisensi_grace=None,
                kuota_transaksi=75,
            )

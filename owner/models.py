from django.db import models
from django.contrib.auth.models import User
import uuid
import datetime
from stock.models import Cabang, Barang

KUOTA_PER_SLOT_BULANAN = 500
HARGA_PER_SLOT_BULANAN = 150_000
HARGA_PER_SLOT_3BULAN  = 400_000
HARGA_PER_SLOT_6BULAN  = 750_000
HARGA_PER_SLOT_TAHUNAN = 1_500_000
HARGA_PER_SLOT_2TAHUN  = 2_800_000

class Owner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_profile')
    nama = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)

    jumlah_slot = models.PositiveIntegerField(default=0)
    kuota_transaksi_pool = models.PositiveIntegerField(default=0)

    lisensi_expired = models.DateTimeField(null=True, blank=True)
    lisensi_grace   = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama} ({self.jumlah_slot} slot)"

    @property
    def is_active(self):
        if self.lisensi_expired is None:
            return False
        return self.lisensi_expired > datetime.datetime.now()

    @property
    def in_grace(self):
        if not self.lisensi_grace:
            return False
        now = datetime.datetime.now()
        return self.lisensi_expired < now <= self.lisensi_grace

    @property
    def bisa_transaksi(self):
        return (self.is_active or self.in_grace) and self.kuota_transaksi_pool > 0

    @property
    def sisa_hari_grace(self):
        if not self.lisensi_grace:
            return 0
        return max(0, (self.lisensi_grace - datetime.datetime.now()).days)

    @property
    def slot_terpakai(self):
        return self.cabang_korporasi.filter(is_gudang=False).count()

    @property
    def slot_tersedia(self):
        return max(0, self.jumlah_slot - self.slot_terpakai)


class TransferStok(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Menunggu Persetujuan'),
        (STATUS_APPROVED, 'Disetujui'),
        (STATUS_REJECTED, 'Ditolak'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner         = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='transfers')
    cabang_asal   = models.ForeignKey(Cabang, on_delete=models.RESTRICT, related_name='transfer_keluar')
    cabang_tujuan = models.ForeignKey(Cabang, on_delete=models.RESTRICT, related_name='transfer_masuk')
    barang_asal   = models.ForeignKey(Barang, on_delete=models.RESTRICT, related_name='transfer_dari')
    barang_tujuan = models.ForeignKey(Barang, on_delete=models.RESTRICT, related_name='transfer_ke', null=True, blank=True)
    jumlah        = models.PositiveIntegerField()
    catatan       = models.CharField(max_length=200, blank=True)
    catatan_owner = models.CharField(max_length=200, blank=True)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    nomor_faktur  = models.CharField(max_length=10, blank=True, unique=False)
    created_by    = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True, related_name='transfer_dibuat')
    approved_by   = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True, related_name='transfer_disetujui')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transfer {self.jumlah} {self.barang_asal.nama} dari {self.cabang_asal} → {self.cabang_tujuan} [{self.status}]"


class RequestMasterBarang(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_CONFLICT  = 'conflict'   # barcode konflik, owner perlu ganti
    STATUS_APPROVED  = 'approved'
    STATUS_REJECTED  = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING,  'Menunggu Persetujuan'),
        (STATUS_CONFLICT, 'Barcode Konflik'),
        (STATUS_APPROVED, 'Disetujui'),
        (STATUS_REJECTED, 'Ditolak'),
    ]

    owner          = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='request_master_barang')
    cabang         = models.ForeignKey(Cabang, on_delete=models.RESTRICT, related_name='request_barang')
    # Data barang yang diminta
    barcode        = models.CharField(max_length=100)
    nama           = models.CharField(max_length=200)
    satuan         = models.CharField(max_length=20, default='PCS')
    harga_beli     = models.IntegerField(default=0)
    harga_ecer     = models.IntegerField(default=0)
    harga_grosir   = models.IntegerField(default=0)
    min_beli_grosir = models.IntegerField(default=0)
    keterangan     = models.CharField(max_length=200, blank=True)
    # Status & catatan
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    catatan_toko   = models.CharField(max_length=200, blank=True)
    catatan_owner  = models.CharField(max_length=200, blank=True)
    barcode_baru   = models.CharField(max_length=100, blank=True)  # jika barcode konflik
    # Tracking
    created_by     = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request {self.nama} dari {self.cabang.nama_toko} [{self.status}]"


class OrderBarang(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_DIPROSES  = 'diproses'   # owner sedang memproses
    STATUS_DIKIRIM   = 'dikirim'    # sudah didistribusikan (PengirimanGudang dibuat)
    STATUS_DITOLAK   = 'ditolak'
    STATUS_CHOICES = [
        (STATUS_PENDING,  'Menunggu Persetujuan'),
        (STATUS_DIPROSES, 'Diproses Owner'),
        (STATUS_DIKIRIM,  'Sudah Dikirim'),
        (STATUS_DITOLAK,  'Ditolak'),
    ]

    owner          = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='order_masuk')
    cabang         = models.ForeignKey(Cabang, on_delete=models.RESTRICT, related_name='order_barang')
    nomor_order    = models.CharField(max_length=10, unique=True)
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    catatan_toko   = models.CharField(max_length=200, blank=True)
    catatan_owner  = models.CharField(max_length=200, blank=True)
    created_by     = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.nomor_order} dari {self.cabang.nama_toko}"


class OrderBarangItem(models.Model):
    order           = models.ForeignKey(OrderBarang, on_delete=models.CASCADE, related_name='item_set')
    barcode         = models.CharField(max_length=100)
    nama_barang     = models.CharField(max_length=200, blank=True)
    jumlah_order    = models.PositiveIntegerField()
    jumlah_disetujui = models.PositiveIntegerField(default=0)
    stok_gudang     = models.IntegerField(default=0)   # snapshot stok saat diproses
    catatan         = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.nama_barang or self.barcode} × {self.jumlah_order}"


class PengirimanGudang(models.Model):
    STATUS_DRAFT    = 'draft'
    STATUS_DIKIRIM  = 'dikirim'    # gudang sudah kirim, toko belum konfirmasi
    STATUS_SELESAI  = 'selesai'    # semua item dikonfirmasi toko
    STATUS_SEBAGIAN = 'sebagian'   # ada item dikembalikan
    STATUS_CHOICES  = [
        (STATUS_DRAFT,   'Draft'),
        (STATUS_DIKIRIM, 'Dalam Pengiriman'),
        (STATUS_SELESAI, 'Selesai'),
        (STATUS_SEBAGIAN,'Selesai (Ada Pengembalian)'),
    ]

    owner            = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='pengiriman_gudang')
    cabang_tujuan    = models.ForeignKey(Cabang, on_delete=models.RESTRICT, related_name='penerimaan_gudang')
    nomor_pengiriman = models.CharField(max_length=10, unique=True)
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DIKIRIM)
    catatan          = models.CharField(max_length=200, blank=True)
    created_by       = models.ForeignKey(User, on_delete=models.RESTRICT, null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pengiriman {self.nomor_pengiriman} → {self.cabang_tujuan.nama_toko}"

    @property
    def semua_dikonfirmasi(self):
        return not self.item_set.filter(status=PengirimanGudangItem.STATUS_PENDING).exists()

    @property
    def ada_pengembalian_pending(self):
        return self.item_set.filter(status=PengirimanGudangItem.STATUS_DIKEMBALIKAN).exists()


class PengirimanGudangItem(models.Model):
    STATUS_PENDING            = 'pending'          # menunggu konfirmasi toko
    STATUS_DITERIMA           = 'diterima'          # toko konfirmasi → stok toko +
    STATUS_DIKEMBALIKAN       = 'dikembalikan'      # toko tolak → menunggu konfirmasi owner
    STATUS_KONFIRMASI_GUDANG  = 'kembali_gudang'    # owner konfirmasi → stok gudang +
    STATUS_CHOICES = [
        (STATUS_PENDING,           'Menunggu Konfirmasi Toko'),
        (STATUS_DITERIMA,          'Diterima Toko'),
        (STATUS_DIKEMBALIKAN,      'Dikembalikan (Menunggu Konfirmasi Gudang)'),
        (STATUS_KONFIRMASI_GUDANG, 'Kembali ke Gudang'),
    ]

    pengiriman    = models.ForeignKey(PengirimanGudang, on_delete=models.CASCADE, related_name='item_set')
    barang_gudang = models.ForeignKey(Barang, on_delete=models.RESTRICT, related_name='pengiriman_item')
    jumlah_dikirim   = models.PositiveIntegerField()
    jumlah_diterima  = models.PositiveIntegerField(default=0)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    catatan_toko     = models.CharField(max_length=200, blank=True)
    catatan_gudang   = models.CharField(max_length=200, blank=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.barang_gudang.nama} × {self.jumlah_dikirim} [{self.status}]"

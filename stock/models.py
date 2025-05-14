from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
import random

SATUAN = [
    ('PCS','PCS'),
    ('PACK','PACK')
]

PEMBAYARAN = [
    ('1','Bulanan'),
    ('3','Per Tiga Bulanan'),
    ('6','Per Semester'),
    ('12','Per 1 Tahun'),
    ('24','Per 2 Tahun')
]

def prefixGenerator():
    while True:
        try:
            prefix = "".join([chr(97+int(random.random()*25)) for x in range(0,4)])
            cabang = Cabang.objects.get(prefix=prefix)
        except:
            return prefix 

class DaftarPaket(models.Model):
    paket = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4)
    nama=models.CharField(max_length=200,default="")
    max_transaksi=models.IntegerField(default=0)
    max_user_login = models.IntegerField(default=0)
    # is_download_transaksi = models.BooleanField(default=True)
    # is_tambah_barang = models.BooleanField(default=True)
    # is_download_barang = models.BooleanField(default=True)
    # is_laporan_transaksi = models.BooleanField(default=True)
    harga_per_bulan = models.PositiveIntegerField(default=0)
    harga_per_tiga_bulan = models.PositiveIntegerField(default=0)
    harga_per_enam_bulan = models.PositiveIntegerField(default=0)
    harga_per_tahun = models.PositiveIntegerField(default=0)
    harga_per_dua_tahun = models.PositiveIntegerField(default=0)
    disc = models.IntegerField(default=0)

    def __str__(self):
        return self.nama

class Cabang(models.Model):
    nama_toko = models.CharField(max_length=20,default="Nama Toko")
    prefix = models.CharField(max_length=5,blank=True,null=True) #randomize
    token = models.UUIDField(auto_created=True,editable=True,default=uuid.uuid4)
    nama_cabang = models.CharField(max_length=15,default="Cabang1")
    alamat_toko = models.CharField(max_length=30,default="Jalan...")
    telpon = models.CharField(max_length=15,default="081234567890")
    keterangan = models.CharField(max_length=200,default="",null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(max_length=200,blank=True,null=True)
    kuota_transaksi = models.IntegerField(default=99999999)
    jumlah_kasir = models.IntegerField(default=0)
    lisensi_expired = models.DateTimeField(null=True,blank=True)
    lisensi_grace = models.DateTimeField(null=True,blank=True)
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,default="",related_name="paket_cabang",null=True,blank=True)
    last_update_kuota = models.DateTimeField(blank=True,null=True)
    kode_referal = models.CharField(max_length=5,verbose_name="Diisi kode prefix user")
    no_nota = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.nama_toko} - {self.nama_cabang}"

# class PaketCabang(models.Model):
#     cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,default="",related_name="Cabang_Paket")
#     paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,default="",related_name="paket_cabang")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     expired = models.DateTimeField(null=True)
#     is_active = models.BooleanField(default=False)

class Pembayaran(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,primary_key=True,default=uuid.uuid4)
    user = models.ForeignKey(User,on_delete=models.RESTRICT)
    midtrans_token = models.CharField(max_length=100,null=True,blank=True)
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT)
    harga = models.PositiveIntegerField(default=0)
    jumlah_bulan = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class UserPaket(models.Model):
    user = models.ForeignKey(User,on_delete=models.RESTRICT)
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,related_name="daftar_paket")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user','paket']

class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.RESTRICT)
    nama_lengkap = models.CharField(max_length=30,default="")
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang_user")
    foto = models.ImageField(upload_to="foto_profile",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.cabang}"

class Customer(models.Model):
    customer = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4,primary_key=True,null=False,blank=False)
    nama = models.CharField(max_length=200,default="")
    handphone = models.CharField(max_length=20,default="081")
    alamat = models.CharField(max_length=200,default="")    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User,on_delete=models.RESTRICT,blank=True,null=True)

    def __str__(self):
        return f"{self.nama} - {self.handphone}"

    class Meta:
        unique_together = ['nama','handphone']

class Barang(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,null=True,blank=True,related_name="cabang_toko")
    barcode = models.CharField(max_length=100,default="0")
    nama = models.CharField(max_length=200)
    satuan = models.CharField(max_length=20,choices=SATUAN,default="PCS")
    stok = models.IntegerField(default=0)
    harga_beli = models.IntegerField(default=0)
    harga_ecer = models.IntegerField(default=0)
    harga_grosir = models.IntegerField(default=0)
    min_beli_grosir = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User,on_delete=models.RESTRICT,blank=True,null=True)
    jumlah_dibeli = models.BigIntegerField(default=0)
    keterangan = models.CharField(max_length=200,default="",null=True,blank=True)

    def __str__(self):
        return f"{self.barcode} - {self.nama} - {self.satuan}"

    class Meta:
        unique_together = ['cabang','barcode']

class UploadBarang(models.Model):
    id_upload = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    user= models.ForeignKey(User,on_delete=models.RESTRICT)
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang")

class UploadBarangList(models.Model):
    upload_barang = models.ForeignKey(UploadBarang,on_delete=models.CASCADE)
    barcode = models.CharField(max_length=100,default="0")
    nama = models.CharField(max_length=200)
    satuan = models.CharField(max_length=20,choices=SATUAN,default="PCS")
    stok = models.IntegerField(default=0)
    harga_ecer = models.IntegerField(default=0)
    harga_grosir = models.IntegerField(default=0)
    min_beli_grosir = models.IntegerField(default=0)
    harga_beli = models.IntegerField(default=0)

class LogTransaksi(models.Model):
    transaksi=models.CharField(max_length=100,default="")
    user = models.ForeignKey(User,on_delete=models.RESTRICT,default="",null=True,blank=True)
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,default="",null=True,blank=True)
    keterangan = models.CharField(max_length=200,default="")
    created_at = models.DateTimeField(auto_now_add=True)

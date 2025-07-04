from django.db import models
from stock.models import Cabang,DaftarPaket
import uuid

# Create your models here.
class TokoGetToko(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="referal")
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,related_name='paketnya')
    registrar = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang_baru",blank=True,null=True)
    nilai = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_withdraw = models.BooleanField(default=True)

class MidtransPayment(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,primary_key=True,null=False,blank=False,default=uuid.uuid4)
    midtrans_token = models.CharField(max_length=100,default="")
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,blank=True,null=True)
    total = models.IntegerField(default=0)
    kode_voucher = models.CharField(max_length=100,blank=True,null=True)
    referal_point = models.IntegerField(default=0)
    transaksi = models.CharField(max_length=100,default="") #upgrade lisensi, perpanjangan atau yang lain
    jml_kuota = models.IntegerField(default=0,blank=True,null=True) #jika tambah kuota
    lisensi_expired = models.DateTimeField(null=True,blank=True) #menyimpan informasi pertambahan lisensi
    lisensi_grace = models.DateTimeField(null=True,blank=True) #menyimpan informasi pertambahan lisensi grace period
    is_success = models.BooleanField(default=False)
    kode_toko = models.CharField(max_length=10,blank=True,null=True)
    nama_toko = models.CharField(max_length=100,blank=True,null=True)
    nama_cabang = models.CharField(max_length=100,blank=True,null=True)
    alamat_toko = models.CharField(max_length=100,blank=True,null=True)
    telpon_toko = models.CharField(max_length=100,blank=True,null=True)
    email_toko = models.CharField(max_length=100,blank=True,null=True)
    pemilik_toko = models.CharField(max_length=100,blank=True,null=True)
    password = models.CharField(max_length=100,blank=True,null=True)
    jenis_paket = models.IntegerField(default=0,null=True,blank=True) # 0 untuk bulanan, 1 untuk 3bulanan, 2 untuk 6 bulanan, 3 untuk tahunan dan 4 untuk 2 tahunan
    status_paket = models.CharField(max_length=10,blank=True,null=True)
    kode_referensi = models.CharField(max_length=10,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    daftar_paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,blank=True,null=True)
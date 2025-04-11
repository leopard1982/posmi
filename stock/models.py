from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone

SATUAN = [
    ('PCS','PCS'),
    ('PACK','PACK')
]


class Cabang(models.Model):
    nama = models.CharField(max_length=200,default="")
    keterangan = models.CharField(max_length=200,default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nama} - {self.keterangan}"

class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.RESTRICT)
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang_user")
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
    barcode = models.CharField(max_length=100,default="0")
    nama = models.CharField(max_length=200)
    satuan = models.CharField(max_length=20,choices=SATUAN,default="PCS")
    stok = models.IntegerField(default=0)
    harga_ecer = models.IntegerField(default=0)
    harga_grosir = models.IntegerField(default=0)
    min_beli_grosir = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User,on_delete=models.RESTRICT,blank=True,null=True)

    def __str__(self):
        return f"{self.barcode} - {self.nama} - {self.satuan}"

    class Meta:
        unique_together = ['barcode','nama']

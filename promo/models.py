from django.db import models
from stock.models import Cabang
import uuid

class Promo(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4,primary_key=True)
    nama = models.CharField(max_length=200)
    kode = models.SlugField(max_length=20,unique=True)
    disc = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    end_period = models.DateField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    kuota = models.IntegerField(default=0)
    is_tambah_kuota = models.BooleanField(default=False,null=True,blank=True)
    is_registrasi = models.BooleanField(default=False,blank=True,null=True)
    is_upgrade_lisensi = models.BooleanField(default=False,blank=True,null=True)
    is_perpanjangan = models.BooleanField(default=False,blank=True,null=True)

    def __str__(self):
        return f"{self.kode} - {self.nama}"

class PromoUsed(models.Model):
    promo = models.ForeignKey(Promo,on_delete=models.RESTRICT,null=True,blank=True,related_name="promo_master")
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,null=True,blank=True,related_name="cabang_used")
    created_at = models.DateTimeField(auto_now_add=True)


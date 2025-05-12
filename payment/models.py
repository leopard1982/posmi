from django.db import models
from stock.models import Cabang,DaftarPaket

# Create your models here.
class TokoGetToko(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="referal")
    paket = models.ForeignKey(DaftarPaket,on_delete=models.RESTRICT,related_name='paketnya')
    registrar = models.ForeignKey(Cabang,on_delete=models.RESTRICT,related_name="cabang_baru",blank=True,null=True)
    nilai = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_withdraw = models.BooleanField(default=True)
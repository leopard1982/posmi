from django.db import models
from stock.models import Cabang, Customer, Barang
import uuid
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count
from django.utils import timezone
import datetime

METODE_BAYAR = [
    (0,'cash'),
    (1,'transfer')
]

class TotalPenjualan(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT)
    tanggal = models.DateField(null=True,blank=True)
    total = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together =['cabang','tanggal']

    def __str__(self):
        return f"{self.cabang} - {self.tanggal} : {self.total}"

class Penjualan(models.Model):
    nota = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4,primary_key=True)
    no_nota = models.CharField(max_length=15)
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT)
    user = models.ForeignKey(User,on_delete=models.RESTRICT,related_name="user_login",blank=True,null=True)
    customer = models.ForeignKey(Customer,on_delete=models.RESTRICT,related_name="customer_penjualan",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    items = models.IntegerField(default=0)
    is_paid = models.BooleanField(default=False)
    metode = models.IntegerField(choices=METODE_BAYAR,default=0)
    customer = models.CharField(max_length=200,default="",blank=True,null=True)
    tgl_bayar = models.DateTimeField(null=True,blank=True)
    reprint_nota = models.IntegerField(default=0)

    def __str__(self):
        if self.is_paid:
            status="LUNAS"
        else:
            status="BELUM BAYAR"
        return f"{self.nota} - {self.customer} - {self.total} : {status}"

class PenjualanDetail(models.Model):
    penjualan = models.ForeignKey(Penjualan,on_delete=models.CASCADE)
    barang = models.ForeignKey(Barang,on_delete=models.RESTRICT)
    jumlah = models.IntegerField(default=0)
    harga = models.BigIntegerField(default=0,blank=True,null=True)
    harga_awal = models.BigIntegerField(default=0,blank=True,null=True)
    total = models.BigIntegerField(default=0,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_open = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.penjualan.nota} - {self.barang} - {self.jumlah} - {self.harga} - {self.total}"

    def save(self,*args,**kwargs):
        if not self.is_open:
            jumlah = self.jumlah
            jumlah_min = self.barang.min_beli_grosir
            
            if(jumlah>=jumlah_min):
                self.harga = self.barang.harga_grosir
            else:
                self.harga = self.barang.harga_ecer
            # jika tidak editan maka harga awal disamakan dengan harga kalau dia sudah grosir juga
            self.harga_awal=self.harga
        else:
            # jika editan maka harga awal disesuaikan dengan harga eccer
            self.harga_awal=self.barang.harga_ecer

        self.total = self.jumlah*self.harga
        super(PenjualanDetail,self).save(*args,**kwargs)

        total_jual = PenjualanDetail.objects.all().filter(penjualan=self.penjualan).aggregate(jual=Sum('total'))
        total_items = PenjualanDetail.objects.all().filter(penjualan=self.penjualan).aggregate(items=Count('total'))
        penjualan = Penjualan.objects.get(nota=self.penjualan.nota)
        penjualan.total=total_jual['jual']
        penjualan.items = total_items['items']
        penjualan.save()

    class Meta:
        unique_together = ['penjualan','barang']

class DetailWalet(models.Model):
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT,null=True,blank=True,related_name="cabang_referal")
    cabang_referensi = models.ForeignKey(Cabang,on_delete=models.RESTRICT,null=True,blank=True,related_name="cabang_referensi")
    keterangan = models.CharField(max_length=200,default="")
    created_at = models.DateTimeField(auto_now_add=True)
    jumlah = models.PositiveIntegerField(default=0)
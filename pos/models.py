from django.db import models
from stock.models import Cabang, Customer, Barang
import uuid
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count
from django.utils import timezone
import datetime

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
    cabang = models.ForeignKey(Cabang,on_delete=models.RESTRICT)
    user = models.ForeignKey(User,on_delete=models.RESTRICT,related_name="user_login",blank=True,null=True)
    customer = models.ForeignKey(Customer,on_delete=models.RESTRICT,related_name="customer_penjualan",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    items = models.IntegerField(default=0)
    is_paid = models.BooleanField(default=False)

    # def save(self,*args,**kwargs):
        # tanggalnya = datetime.date(datetime.datetime.now().year,datetime.datetime.now().month,datetime.datetime.now().day)
        # penjualan = Penjualan.objects.all().filter(Q(updated_at__contains=tanggalnya) & Q(is_paid=True)).aggregate(total=Sum('total'))
        # super(Penjualan,self).save(*args,**kwargs)
        # # print(self.updated_at)
 
 
        # try:
        #     totalpenjualan = TotalPenjualan.objects.get(Q(cabang=self.cabang) & Q(tanggal=tanggalnya))
        #     totalpenjualan.total=penjualan['total']
        #     totalpenjualan.save()
        # except:
        #     totalpenjualan = TotalPenjualan()
        #     totalpenjualan.cabang = self.cabang
        #     totalpenjualan.tanggal= tanggalnya
        #     totalpenjualan.total = penjualan['total']
        #     totalpenjualan.save()    
        

    def __str__(self):
        if self.is_paid:
            status="LUNAS"
        else:
            status="BELUM BAYAR"
        return f"{self.nota} [{self.created_at.strftime("%d/%m/%Y")}] - {self.customer} - {self.total} : {status}"

class PenjualanDetail(models.Model):
    penjualan = models.ForeignKey(Penjualan,on_delete=models.CASCADE)
    barang = models.ForeignKey(Barang,on_delete=models.RESTRICT)
    jumlah = models.IntegerField(default=0)
    harga = models.BigIntegerField(default=0,blank=True,null=True)
    total = models.BigIntegerField(default=0,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.penjualan.nota} - {self.barang} - {self.jumlah} - {self.harga} - {self.total}"

    def save(self,*args,**kwargs):
        jumlah = self.jumlah
        jumlah_min = self.barang.min_beli_grosir
        
        if(jumlah>=jumlah_min):
            self.harga = self.barang.harga_grosir
        else:
            self.harga = self.barang.harga_ecer
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
from django.shortcuts import render, HttpResponse
from .models import Promo, PromoUsed
from stock.models import Cabang
from django.db.models import Q
import datetime

# Create your views here.
def getPromo(request):
    promo_list = Promo.objects.all().filter(Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gt=0))
    context = {
        'promo_list':promo_list
    }
    return render(request,'promo/list_promo.html',context)

def cekKodeVoucher(kode,cabang=None):
    kode = kode
    try:
        promo = Promo.objects.get(Q(kode=str(kode).lower()) & Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gte=1))
        if(cabang):
            try:
                promoused = PromoUsed.objects.get(Q(cabang=cabang) & Q(promo=promo))
            except:
                return False
        return True
    except:
        return False
    
def cekKodeToko(kode):
    kode = kode
    try:
        cabang = Cabang.objects.get(prefix=str(kode).lower())
        return True
    except:
        return False
    
def requestKodeVoucher(request):
    kode = request.GET['voucher']
    if len(kode)==0:
        return HttpResponse('')
    available = cekKodeVoucher(kode)
    if available:
        return HttpResponse("<span class='text-success fw-bold'>Kode Voucher Bisa Dipakai! Segera Daftar Sebelum Voucher Habis!</span>")
    else:
        return HttpResponse("<span class='text-danger fw-bold'>Maaf kode voucher tidak bisa dipakai yah. Coba pakai kode voucher lain.</span>")

def requestKodeToko(request):
    kode = request.GET['referensi']
    if len(kode)==0:
        return HttpResponse('')
    available = cekKodeToko(kode)
    if available:
        return HttpResponse("<span class='text-success fw-bold'>Kode Referensi OK.</span>")
    else:
        return HttpResponse("<span class='text-danger fw-bold'>Kode Rerensi Tidak Ditemukan.</span>")
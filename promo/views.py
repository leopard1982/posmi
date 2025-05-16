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

def cekKodeVoucher(kode,toko=None,tipe=None):
    kode = kode
    try:
        print(tipe)
        if tipe=='reg':
            print('reg')
            promo = Promo.objects.get(Q(kode=str(kode).lower()) & Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gte=1) &Q(is_registrasi=True))
        elif tipe=="add":
            print('add')
            promo = Promo.objects.get(Q(kode=str(kode).lower()) & Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gte=1) &Q(is_tambah_kuota=True))

        print(promo)
        if(toko):
            try:
                try:
                    cabang = Cabang.objects.get(prefix=toko)
                    # kalau sudah pernah dipakai langsung return False
                    promoused = PromoUsed.objects.get(Q(cabang=cabang) & Q(promo=promo))
                    return {
                        'status':False,
                        'disc':0
                    }
                except:
                    pass
            except Exception as ex:
                print(ex)
                return {
                    'status':False,
                    'disc':0
                }
        return {
            'status':True,
            'disc':promo.disc
        }
    except Exception as ex:
        print(ex)
        return {
            'status':False,
            'disc':0
        }
    
def cekKodeToko(kode):
    kode = kode
    try:
        cabang = Cabang.objects.get(prefix=str(kode).lower())
        return True
    except:
        return False
    
def requestKodeVoucher(request):
    kode = request.GET['voucher']
    tipe = request.GET['tipe']
    try:
        toko = request.GET['toko']
    except:
        toko = ""
    # tipe: reg=registrasi
    # tipe: upg=upgrade
    # tipe: add=tambah kuota
    # tipe: pnj=perpanjangan lisensi
    if len(kode)==0:
        return HttpResponse('')
    available = cekKodeVoucher(kode=kode,tipe=tipe,toko=toko)
    if available['status']:
        return HttpResponse(f"<span class='text-success fw-bold'>Selamat, Potongan Rp.{available['disc']:,}! Segera Proses Sebelum Voucher Habis!</span>")
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
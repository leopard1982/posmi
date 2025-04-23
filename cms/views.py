from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from pos.models import Penjualan, Barang
from django.db.models import Q,Sum,Count
import datetime


def bulannya(bulannya):
    if bulannya==1:
        return "Januari"
    elif bulannya==2:
        return "Februari"
    elif bulannya==3:
        return "Maret"
    elif bulannya==4:
        return "April"
    elif bulannya==5:
        return "Mei"
    elif bulannya==6:
        return "April"
    elif bulannya==7:
        return "Juli"
    elif bulannya==8:
        return "Agustus"
    elif bulannya==9:
        return "September"
    elif bulannya==10:
        return "Oktober"
    elif bulannya==11:
        return "November"
    elif bulannya==12:
        return "Desember"
    
def cekTotal(data):
    if data==None:
        return 0
    else:
        return data

def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            penjualan = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year))
            total_penjualan_sebulan = penjualan.aggregate(jumlah=Sum('total'))
            total_penjualan_setahun = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(jumlah=Sum('total'))
            bulan = bulannya(datetime.datetime.now().month)
            tahun = datetime.datetime.now().year
            pending_penjualan = Penjualan.objects.all().filter(Q(is_paid=False) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(jumlah=Count('total'))
            jumlah_penjualan = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(jumlah=Count('total'))
            
            # mengisi grafik penjualan
            april = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=4) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            januari = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=1) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            februari = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=2) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            maret = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=3) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            mei = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=5) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            juni = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=6) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            juli = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=7) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            agustus = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=8) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            september = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=9) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            oktober = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=10) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            november = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=11) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            desember = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=12) & Q(updated_at__year=datetime.datetime.now().year)).aggregate(total=Sum('total'))
            
            # mengisi top 5 barang terjual
            barang = Barang.objects.all().filter(cabang=request.user.userprofile.cabang).order_by('-jumlah_dibeli','updated_at')[:5]
            list_nama_barang = []
            list_jumlah_barang = []
            for bar in barang:
                list_nama_barang.append(bar.nama)
                list_jumlah_barang.append(bar.jumlah_dibeli)

            context = {
                'bulan':bulan,
                'tahun':tahun,
                'total_penjualan_sebulan':total_penjualan_sebulan['jumlah'],
                'total_penjualan_setahun':total_penjualan_setahun['jumlah'],
                'pending_penjualan':pending_penjualan['jumlah'],
                'jumlah_penjualan':jumlah_penjualan['jumlah'],
                'januari':cekTotal(januari['total']),
                'april':cekTotal(april['total']),
                'febuari':cekTotal(februari['total']),
                'maret':cekTotal(maret['total']),
                'mei':cekTotal(mei['total']),
                'juni':cekTotal(juni['total']),
                'juli':cekTotal(juli['total']),
                'agustus':cekTotal(agustus['total']),
                'september':cekTotal(september['total']),
                'oktober':cekTotal(oktober['total']),
                'november':cekTotal(november['total']),
                'desember':cekTotal(desember['total']),
                'list_nama_barang':list_nama_barang,
                'list_jumlah_barang':list_jumlah_barang
            }
            return render(request,'administrator/index.html',context)
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
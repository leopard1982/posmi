from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from pos.models import Penjualan, Barang
from django.db.models import Q,Sum,Count
import datetime
from django.contrib.auth.models import User
from .forms import FormInfoToko, FormUserProfile, FormUser, FormBarang
from stock.models import Cabang

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
            pending_penjualan = Penjualan.objects.all().filter(Q(is_paid=False) & Q(cabang=request.user.userprofile.cabang) & Q(created_at__month=datetime.datetime.now().month) & Q(created_at__year=datetime.datetime.now().year)).aggregate(jumlah=Count('total'))
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
            
            # mengisi jumlah transaksi pengguna
            liga_kasir = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=4) & Q(updated_at__year=datetime.datetime.now().year)).values('user').annotate(jumlah=Count('user'))
            nama_kasir = []
            jumlah_transaksi=[]
            for kasir in liga_kasir:
                nama_kasir.append(User.objects.get(id=int(kasir['user'])).username)
                jumlah_transaksi.append(kasir['jumlah'])

            # mengisi jumlah pembayaran cash vs transfer
            liga_metode = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=4) & Q(updated_at__year=datetime.datetime.now().year)).values('metode').annotate(jumlah=Count('metode')).order_by()
            print(liga_metode)
            jumlah_metode = []
            # apakah metode cash?
            try:
                if(liga_metode[0]['metode']==0):
                    # tambahkan jumlah metodenya
                    jumlah_metode.append(liga_metode[0]['jumlah'])
                else:
                    # jika tidak ada maka kasih angka 0
                    jumlah_metode.append(0)
            except:
                jumlah_metode.append(0)
            # apakah metode transfer?
            try:
                if(liga_metode[1]['metode']==1):
                    jumlah_metode.append(liga_metode[1]['jumlah'])
                else:
                    jumlah_metode.append(0)
            except:
                jumlah_metode.append(0)
            
            print(jumlah_metode)

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
                'list_jumlah_barang':list_jumlah_barang,
                'nama_kasir':nama_kasir,
                'jumlah_transaksi':jumlah_transaksi,
                'jumlah_metode':jumlah_metode
            }
            return render(request,'administrator/index.html',context)
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def infoToko(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            if(request.method=="POST"):
                cabang = Cabang.objects.get(id=request.user.userprofile.cabang.id)
                cabang.nama_toko = request.POST['nama_toko']
                cabang.nama_cabang = request.POST['nama_cabang']
                cabang.alamat_toko = request.POST['alamat_toko']
                cabang.telpon = request.POST['telpon']
                cabang.keterangan = request.POST['keterangan']
                cabang.save()
                messages.add_message(request,messages.SUCCESS,"Data Informasi Toko Berhasil Diubah.")
                return HttpResponseRedirect('/cms/')
            
            forminfotoko = FormInfoToko(instance=request.user.userprofile.cabang)
            context = {
                'forms':forminfotoko
            }
            return render(request,'administrator/components/info_toko.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def daftarBarang(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            barangs = Barang.objects.all().filter(cabang=request.user.userprofile.cabang)
            context = {
                'barangs':barangs
            }
            return render(request,'administrator/components/list_barang.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def transaksiBulanBerjalan(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            transaksi = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=4) & Q(updated_at__year=datetime.datetime.now().year))
            context = {
                'transaksi':transaksi
            }
            return render(request,'administrator/components/history_bulan_berjalan.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def transaksiBulanLain(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            if request.method=="POST":
                transaksi = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=int(request.POST['bulan'])) & Q(updated_at__year=int(request.POST['tahun'])))
                context = {
                    'transaksi':transaksi
                }
                return render(request,'administrator/components/history_bulan_lain.html',context)
            return render(request,'administrator/components/filter_history.html')
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def profilSaya(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            if request.method=="POST":
                print(request.POST)
            formuserprofile = FormUserProfile()
            formuser = FormUser()
            context = {
                'formprofile':formuserprofile,
                'formuser':formuser
            }
            return render(request,'administrator/components/profile.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def editBarang(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            if request.method=="POST":
                try:
                    id_barang = request.GET['id']
                    barang = Barang.objects.get(Q(id=id_barang) & Q(cabang=request.user.userprofile.cabang))
                    barang.barcode=request.POST['barcode']
                    barang.nama=request.POST['nama']
                    barang.satuan=request.POST['satuan']
                    barang.stok = int(request.POST['stok'])
                    barang.harga_ecer=int(request.POST['harga_ecer'])
                    barang.harga_grosir=int(request.POST['harga_grosir'])
                    barang.save()
                    messages.add_message(request,messages.SUCCESS,f"Update Informasi '{barang.nama}' Berhasil.")
                except Exception as ex:
                    print(ex)
                    messages.add_message(request,messages.SUCCESS,"Update Barang Gagal.")
                return HttpResponseRedirect('/cms/')
            try:
                id_barang = request.GET['id']
                barang = Barang.objects.get(Q(id=id_barang) & Q(cabang=request.user.userprofile.cabang))
                form = FormBarang(instance=barang)
                context = {
                    'form':form,
                    'id_barang':id_barang
                }
                return render(request,'administrator/components/edit_barang.html',context)
            except Exception as ex:
                print(ex)
                return HttpResponseRedirect('/cms/')
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
from django.shortcuts import render, HttpResponseRedirect
from .models import Penjualan, PenjualanDetail
from stock.models import Barang, Cabang
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.conf import settings
import datetime
from django.contrib.auth import authenticate,login,logout

# Create your views here.
def index(request):
    toko = settings.NAMA_TOKO
    tanggal = datetime.datetime.now()
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        if request.method=="POST":
            try:
                nota = request.GET['nota']
            except:
                nota=""

            kode = request.POST['kode']
                
            if nota:
                penjualan= Penjualan.objects.get(nota=nota)
            else:
                cabang = request.user.userprofile.cabang
                penjualan=Penjualan()
                penjualan.cabang=cabang
                penjualan.user=user
                penjualan.save()
                nota=penjualan.nota
            try:
                print(kode)
                if(kode):
                    barang = Barang.objects.get(barcode=kode)
                    messages.add_message(request,messages.SUCCESS,f"{barang.nama} berhasil ditambahkan.")
                    try:
                        penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                        penjualandetail.jumlah=penjualandetail.jumlah+1
                        penjualandetail.save()
                    except Exception as ex:
                        print(ex)
                        penjualandetail = PenjualanDetail()
                        penjualandetail.jumlah=1
                        penjualandetail.penjualan=penjualan
                        penjualandetail.barang=barang
                        penjualandetail.save()
                else:
                    messages.add_message(request,messages.SUCCESS,"Maaf barang dengan kode tersebut belum ada.")    
            except Exception as ex:
                if (kode):
                    messages.add_message(request,messages.SUCCESS,"Maaf barang dengan kode tersebut belum ada.")
            return HttpResponseRedirect(f'/?nota={nota}')
    else:
        user=None


    try:
        # diubah supaya bs fleksible
        try:
            nota = request.GET['nota']
        except:
            nota=""
        print(nota)
        if(nota):
            penjualan = Penjualan.objects.get(nota=nota)
            penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
            nota = penjualan.nota
            total = penjualan.total
            jumlah_item = penjualan.items
        else:
            penjualandetail=None
            nota=""
            total=0
            jumlah_item=0
    except Exception as ex:
        penjualandetail=None
        nota=""
        print(ex)
        total=0
        jumlah_item=0

    barang = Barang.objects.all()

    penjualan_pending = Penjualan.objects.all().filter(Q(is_paid=False) & Q(user=user)).order_by('-created_at')
    jumlah_penjualan_pending = penjualan_pending.count()

    context = {
        'penjualandetail':penjualandetail,
        'nota':nota,
        'total':total,
        'jumlah_item':jumlah_item,
        'barang':barang,
        'jml_barang':barang.count(),
        'toko':toko,
        'tanggal':tanggal,
        'penjualan_pending':penjualan_pending,
        'jumlah_penjualan_pending':jumlah_penjualan_pending
    }
    return render(request,'pos/pos.html',context)

def kurangiItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated:
        try:
            nota = request.GET['nota']
            id_barang = request.GET['id']
            try:
                penjualan = Penjualan.objects.get(nota=nota)
                barang = Barang.objects.get(id=int(id_barang))
                penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                if penjualandetail.jumlah==1:
                    penjualandetail.delete()
                    penjualan.items-=1
                    penjualan.save()
                    messages.add_message(request,messages.SUCCESS,f'{barang.nama} dihapus karena dalam daftar menjadi nol.')
                else:
                    penjualandetail.jumlah -= 1
                    penjualandetail.save()    
                    messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah dikurangi 1.')
                
                if penjualan.items==0:
                    penjualan.delete()
                    return HttpResponseRedirect('/')
                
            except:
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(page)    
        except:
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
            return HttpResponseRedirect(page)
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
        return HttpResponseRedirect(page)

def tambahItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated:
        try:
            nota = request.GET['nota']
            id_barang = request.GET['id']
            try:
                penjualan = Penjualan.objects.get(nota=nota)
                barang = Barang.objects.get(id=int(id_barang))
                penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                penjualandetail.jumlah += 1
                penjualandetail.save()    
                messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah ditambah 1.')
                return HttpResponseRedirect(f"{page}?nota={nota}")
            except:
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(page)    
        except:
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
    return HttpResponseRedirect(page)

def ubahItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated:
        try:
            nota = request.GET['nota']
            id_barang = int(request.GET['id'])
            jumlah = int(request.POST['jumlah'])
            try:
                penjualan = Penjualan.objects.get(nota=nota)
                barang = Barang.objects.get(id=int(id_barang))
                penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                if(int(jumlah)==0):
                    penjualandetail.delete()
                    penjualan.items-=1
                    penjualan.save()
                    messages.add_message(request,messages.SUCCESS,f'{barang.nama} dihapus karena dalam daftar menjadi nol.')
                else:
                    penjualandetail.jumlah = jumlah
                    penjualandetail.save()    
                    messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah diupdate menjadi {jumlah}.')
                
                if penjualan.items==0:
                    penjualan.delete()
                    return HttpResponseRedirect('/')

            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(page)    
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
    return HttpResponseRedirect(page)

def tambahBarang(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"

    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        cabang = request.user.userprofile.cabang
        try:
            nota = request.GET['nota']
        except:
            messages.add_message(request,messages.SUCCESS,'Id Nota belum ada...')
            return HttpResponseRedirect("/")

        try:
            id_barang = request.GET['id']
        except Exception as ex:
            print(ex)
            # messages.add_message(request,messages.SUCCESS,'Kode Barang belum ada.')
            return HttpResponseRedirect(f"/?nota={nota}")
        
        print(nota)
        
        if(nota):
            try:
                penjualan = Penjualan.objects.get(nota=nota)
                try:
                    barang = Barang.objects.get(id=int(id_barang))
                except:
                    messages.add_message(request,messages.SUCCESS,'Kode Barang tidak ditemukan.')
                    return HttpResponseRedirect(f"/?nota={nota}")   
                
                try:
                    penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                    penjualandetail.jumlah += 1
                    penjualandetail.save()
                except:
                    penjualandetail = PenjualanDetail()
                    penjualandetail.barang=barang
                    penjualandetail.jumlah=1
                    penjualandetail.penjualan=penjualan
                    penjualandetail.save()    
                messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah ditambah 1.')
            except:
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(f"?nota={nota}")    
        else:
            penjualan = Penjualan()
            penjualan.cabang=cabang
            penjualan.user=user
            penjualan.save()
            barang = Barang.objects.get(id=int(id_barang))
            penjualandetail = PenjualanDetail()
            penjualandetail.penjualan=penjualan
            penjualandetail.jumlah=1
            penjualandetail.barang=barang
            penjualandetail.save()
            messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah ditambah 1.')
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
    return HttpResponseRedirect(f"?nota={penjualan.nota}")

def hapusTransaksi(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    if request.user.is_authenticated:
        print('hallo')
        try:
            nota = request.GET['nota']
            try:
                Penjualan.objects.all().filter(nota=nota).delete()
                messages.add_message(request,messages.SUCCESS,f'Nota Penjualan dengan id {nota} berhasil dihapus...')
                return HttpResponseRedirect(page)
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,'Nota Penjualan tidak diketemukan...')
                return HttpResponseRedirect(page)
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,'Nota Penjualan tidak diketemukan...')
            return HttpResponseRedirect(page)
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
        return HttpResponseRedirect(page)
        
def loginkan(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        if request.method=="POST":
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username,password=password)
            if(user):
                login(request,user)
                messages.add_message(request,messages.SUCCESS,f"Selamat datang {username}")
                return HttpResponseRedirect('/')
            else:
                messages.add_message(request,messages.SUCCESS,f"Username dan Password tidak sesuai, silakan ulangi kembali.")
        toko = settings.NAMA_TOKO
        context = {
            'toko':toko
        }
        return render(request,'pos/login.html',context)
    
def logoutkan(request):
    logout(request)
    return HttpResponseRedirect('/login')
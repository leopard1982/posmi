from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from pos.models import Penjualan, Barang, DetailWalet
from django.db.models import Q,Sum,Count
import datetime
from django.contrib.auth.models import User
from .forms import FormInfoToko, FormUserProfile, FormUser, FormBarang
from stock.models import Cabang,UserProfile
from django.urls import reverse
from django.http import FileResponse
from django.conf import settings
import os
import pandas
from stock.models import UploadBarang,UploadBarangList,LogTransaksi
import uuid
import random
from posmimail import posmiMail
from pos.models import Penjualan,PenjualanDetail


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
    
def addLog(user,cabang,transaksi,keterangan):
    try:
        if(user):
            logtransaksi = LogTransaksi()
            logtransaksi.user=user
            logtransaksi.cabang=cabang
            logtransaksi.transaksi=transaksi
            logtransaksi.keterangan=keterangan
            logtransaksi.save()
        else:
            logtransaksi = LogTransaksi()
            logtransaksi.transaksi=transaksi
            logtransaksi.keterangan=keterangan
            logtransaksi.save()
        return True
    except:
        return False
    
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
            
            jumlah_barang = Barang.objects.all().filter(cabang=request.user.userprofile.cabang).count()

            barang = Barang.objects.all().filter(cabang=request.user.userprofile.cabang).order_by('-jumlah_dibeli','updated_at')[:5]
            list_nama_barang = []
            list_jumlah_barang = []
            for bar in barang:
                list_nama_barang.append(bar.nama)
                list_jumlah_barang.append(bar.jumlah_dibeli)
            
            print(request.user.userprofile.cabang)
            # mengisi jumlah transaksi pengguna
            liga_kasir = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year)).values('user').annotate(jumlah=Count('user'))
            nama_kasir = []
            jumlah_transaksi=[]
            for kasir in liga_kasir:
                nama_kasir.append(User.objects.get(id=int(kasir['user'])).username)
                jumlah_transaksi.append(kasir['jumlah'])
            
            print(liga_kasir)

            # mengisi jumlah pembayaran cash vs transfer
            liga_metode = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year)).values('metode').annotate(jumlah=Count('metode')).order_by()
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
                'jumlah_metode':jumlah_metode,
                'jumlah_barang':jumlah_barang
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
        detailwallet=None
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
            cabang = request.user.userprofile.cabang
            detailwallet = DetailWalet.objects.all().filter(cabang=cabang)
            wallet = cabang.wallet
            kode_toko = cabang.prefix
            context = {
                'forms':forminfotoko,
                'wallet':wallet,
                'kode_toko':kode_toko,
                'detailwallet':detailwallet
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
                'barangs':barangs,
                'jumlah_barang':barangs.count()
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
            transaksi = Penjualan.objects.all().filter(Q(is_paid=True) & Q(cabang=request.user.userprofile.cabang) & Q(updated_at__month=datetime.datetime.now().month) & Q(updated_at__year=datetime.datetime.now().year))
            bulan = bulannya(datetime.datetime.now().month)
            tahun = datetime.datetime.now().year
            context = {
                'transaksi':transaksi,
                'bulannya':bulan,
                'tahunnya':tahun
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
                    barang.harga_beli = int(request.POST['harga_beli'])
                    barang.keterangan = request.POST['keterangan']
                    barang.save()
                    addLog(request.user,request.user.userprofile.cabang,"edit barang",f"Edit Barang {barang.nama} ({barang.id})Berhasil")
                    messages.add_message(request,messages.SUCCESS,f"Update Informasi '{barang.nama}' Berhasil.")
                except Exception as ex:
                    print(ex)
                    addLog(request.user,request.user.userprofile.cabang,"edit barang",f"Edit Barang {barang.nama} ({barang.id}) Gagal")
                    messages.add_message(request,messages.SUCCESS,"Update Barang Gagal.")
                return HttpResponseRedirect(reverse('daftar_barang'))
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
    
def tambahBarang(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            if request.method=="POST":
                # print(request.POST)
                # print(request.FILES)
                tanggal_upload=datetime.datetime.now()
                df = pandas.read_excel(request.FILES['file'])
                # print(df)
                list_informasi=[]
                uploadbarang = UploadBarang()
                uploadbarang.cabang = request.user.userprofile.cabang
                uploadbarang.user = request.user
                uploadbarang.save()
                for index,data in df.iterrows():
                    try:
                        barcode = int(data['barcode'])
                        nama = data['nama']
                        satuan = str(data['satuan']).upper()
                        try:
                            stok=int(data['stok'])
                        except Exception as ex:
                            # print(ex)
                            stok=0
                        try:
                            harga_ecer = int(data['harga_ecer'])
                        except Exception as ex:
                            # print(ex)
                            harga_ecer=0
                        try:
                            harga_grosir=int(data['harga_grosir'])
                        except Exception as ex:
                            # print(ex)
                            harga_grosir=0
                        try:
                            min_beli_grosir=int(data['min_beli_grosir'])
                        except Exception as ex:
                            # print(ex)
                            min_beli_grosir=0
                        try:
                            harga_beli=int(data['harga_beli'])
                        except Exception as ex:
                            # print(ex)
                            harga_beli=0
                        try:
                            keterangan = data['keterangan']
                        except:
                            keterangan=None

                        informasi = {
                            'barcode':barcode,
                            'nama':nama,
                            'satuan':satuan,
                            'stok':stok,
                            'harga_ecer':harga_ecer,
                            'harga_grosir':harga_grosir,
                            'harga_beli':harga_beli,
                            'min_beli_grosir':min_beli_grosir,
                            'keterangan':keterangan
                        }
                        # print(informasi)
                        list_informasi.append(informasi)
                        uploadbaranglist = UploadBarangList()
                        uploadbaranglist.upload_barang=uploadbarang
                        uploadbaranglist.barcode=barcode
                        uploadbaranglist.nama=nama
                        uploadbaranglist.satuan = satuan
                        uploadbaranglist.stok=stok
                        uploadbaranglist.harga_ecer=harga_ecer
                        uploadbaranglist.harga_grosir=harga_grosir
                        uploadbaranglist.min_beli_grosir=min_beli_grosir
                        uploadbaranglist.harga_beli=harga_beli
                        uploadbaranglist.keterangan=keterangan
                        uploadbaranglist.save()

                    except Exception as ex:
                        print(ex)
                        barcode = None
                    # if(barcode):
                    #     print(barcode)

                # print(header)
                jumlah_barang = len(list_informasi)
                messages.add_message(request,messages.SUCCESS,"Silakan Cek terlebih dahulu barang yang masuk daftar upload.")
                context = {
                    'tanggal_upload':tanggal_upload,
                    'total_barang':jumlah_barang,
                    'list_informasi':list_informasi,
                    'id_uploadbarang':str(uploadbarang.id_upload)
                }
                return render(request,'administrator/components/tambah_barang_list.html',context)
            context={}
            return render(request,'administrator/components/tambah_barang.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def downloadTemplate(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            lokasi_template = os.path.join(settings.BASE_DIR,'static/template/template.xlsx')
            file = open(lokasi_template,'rb')
            response = FileResponse(file,as_attachment=True,filename="template_barang_upload.xlsx")
            return response
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def konfirmasiUpload(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            try:
                id = request.GET['id']
                uploadbarang = UploadBarang.objects.get(id_upload=id)
                uploadbaranglist = UploadBarangList.objects.all().filter(upload_barang=uploadbarang)
                
                for baranglist in uploadbaranglist:
                    try:
                        barang = Barang.objects.get(Q(cabang = request.user.userprofile.cabang) & Q(barcode=baranglist.barcode))
                        barang.satuan=baranglist.satuan
                        barang.stok=baranglist.stok
                        barang.harga_ecer = baranglist.harga_ecer
                        barang.harga_grosir = baranglist.harga_grosir
                        barang.min_beli_grosir = baranglist.min_beli_grosir
                        barang.harga_beli = baranglist.harga_beli
                        barang.keterangan = baranglist.keterangan
                        barang.save()
                    except Exception as ex:
                        print(ex)
                        barang = Barang()
                        barang.nama = baranglist.nama
                        barang.barcode = baranglist.barcode
                        barang.cabang=request.user.userprofile.cabang
                        barang.satuan=baranglist.satuan
                        barang.stok=baranglist.stok
                        barang.harga_ecer = baranglist.harga_ecer
                        barang.harga_grosir = baranglist.harga_grosir
                        barang.min_beli_grosir = baranglist.min_beli_grosir
                        barang.harga_beli = baranglist.harga_beli
                        barang.keterangan = baranglist.keterangan
                        barang.save()
                addLog(request.user,request.user.userprofile.cabang,"tambah barang",f"Menambahkan  {len(uploadbaranglist)} Barang Berhasil.")
                uploadbarang.delete()
                barangs = Barang.objects.all().filter(cabang=request.user.userprofile.cabang)
                context = {
                    'barangs':barangs,
                    'jumlah_barang':barangs.count()
                }
                messages.add_message(request,messages.SUCCESS,"Update data barang sudah berhasil. Silakan cek data barang.")
                return render(request,'administrator/components/list_barang.html',context)
            except Exception as ex:
                print(ex)
                addLog(request.user,request.user.userprofile.cabang,"tambah barang",f"Menambahkan   Barang Gagal.")
                messages.add_message(request,messages.SUCCESS,"Terjadi kesalahan upload barang, silakan coba lagi...")
                context={}
                return render(request,'administrator/components/tambah_barang.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def hapusBarang(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            try:
                id=request.GET['id']
                barang=Barang.objects.get(Q(cabang=request.user.userprofile.cabang) & Q(id=id))
                barang.delete()
                messages.add_message(request,messages.SUCCESS,"Barang Berhasil Dihapus.")
                addLog(request.user,request.user.userprofile.cabang,"hapus barang",f"Hapus Barang {barang.nama} ({barang.id}) Berhasil.")
            except Exception as ex:
                print(ex)
                addLog(request.user,request.user.userprofile.cabang,"hapus barang",f"Hapus Barang {barang.nama} ({barang.id}) Gagal.")
                messages.add_message(request,messages.SUCCESS,"Terjadi kesalahan hapus barang, barang yang sudah pernah dijual tidak dapat dihapus.")
            barangs = Barang.objects.all().filter(cabang=request.user.userprofile.cabang)
            context = {
                    'barangs':barangs,
                    'jumlah_barang':barangs.count()
                }
            return render(request,'administrator/components/list_barang.html',context)
        else:
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def downloadBarang(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            barcode=[]
            nama=[]
            satuan=[]
            stok=[]
            harga_ecer=[]
            harga_grosir=[]
            min_beli_grosir=[]
            harga_beli=[]
            keterangan=[]

            barangs = Barang.objects.all().filter(cabang=request.user.userprofile.cabang).order_by('nama')
            for barang in barangs:
                barcode.append(barang.barcode)
                nama.append(barang.nama)
                satuan.append(barang.satuan)
                stok.append(barang.stok)
                harga_beli.append(barang.harga_beli)
                harga_ecer.append(barang.harga_ecer)
                harga_grosir.append(barang.harga_grosir)
                min_beli_grosir.append(barang.min_beli_grosir)
                keterangan.append(barang.keterangan)

            df = pandas.DataFrame({
                'barcode':barcode,
                'nama':nama,
                'satuan':satuan,
                'stok':stok,
                'harga_beli':harga_beli,
                'harga_ecer':harga_ecer,
                'harga_grosir':harga_grosir,
                'min_beli_grosir':min_beli_grosir,
                'keterangan':keterangan
            })

            lokasi_file = os.path.join(settings.BASE_DIR,f'media/download/barang/{request.user.userprofile.cabang.token}.xlsx')

            df.to_excel(lokasi_file,index=False)

            file = open(lokasi_file,'rb')
            addLog(request.user,request.user.userprofile.cabang,"download barang",f"Download daftar Barang Berhasil.")
            response = FileResponse(file,as_attachment=True,filename=f"{request.user.userprofile.cabang.nama_toko}.xlsx")
            return response
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')

def viewLog(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            log_list = LogTransaksi.objects.all().filter(cabang=request.user.userprofile.cabang).order_by('-created_at')
            context = {
                'log_list':log_list
            }
            return render(request,'administrator/components/log.html',context)
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
    
def daftarKasir(request):
    list_user = User.objects.all().filter(userprofile__cabang=request.user.userprofile.cabang)
    context = {
        'list_user':list_user
    }
    return render(request,'administrator/components/list_user.html',context)

def tambahKasir(request):
    if request.method=="POST":
        pass1 = request.POST['password1']
        pass2 = request.POST['password2']
        print(pass1)
        print(pass2)
        if pass1!=pass2:
            messages.add_message(request,messages.SUCCESS,'Penambahan kasir gagal, password dan konfirmasinya tidak sama. Silakan ulangi kembali.')
            return render(request,'administrator/components/tambah_user.html')
        else:
            try:
                nama_lengkap = request.POST['nama_lengkap']
                id_cabang = request.user.userprofile.cabang.id
                cabang = Cabang.objects.get(id=id_cabang)
                jumlah_kasir = cabang.jumlah_kasir+1
                userid = f"{cabang.prefix}{jumlah_kasir}"
                print(userid)
                try:
                    usernya = User()
                    usernya.username=userid
                    usernya.password=pass1
                    usernya.save()
                    usernya.set_password(pass1)
                    usernya.save()


                    cabang.jumlah_kasir=cabang.jumlah_kasir+1
                    cabang.save()
                except:
                    jumlah_kasir = cabang.jumlah_kasir+2
                    userid = f"{cabang.prefix}{jumlah_kasir}"
                    usernya = User()
                    usernya.username=userid
                    usernya.password=pass1
                    usernya.save()
                    usernya.set_password(pass1)
                    usernya.save()

                    cabang.jumlah_kasir=cabang.jumlah_kasir+2
                    cabang.save()

                userprofile = UserProfile()
                userprofile.user=usernya
                userprofile.cabang=cabang
                userprofile.nama_lengkap=nama_lengkap
                userprofile.is_active=True
                userprofile.save()

                message = f"Selamat!\n\nUser {nama_lengkap} dengan username {usernya} dan password {pass1} berhasil ditambahkan.\n\nUser sudah aktif dan sudah bisa untuk melakukan transaksi penjualan.\n\nUntuk login bisa melakukan akses ke: https://posmi.pythonanywhere.com/login/ \n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"
                posmiMail("Penambahan User Kasir",message=message,address=cabang.email)
                
                return HttpResponseRedirect('/cms/kasir/')
            except Exception as ex:
                print(ex)
                return HttpResponseRedirect('/cms/kasir/tambah/')
    else:
        return render(request,'administrator/components/tambah_user.html')
    
def detailPenjualan(request):
    try:
        nota = request.GET['id']
        penjualan = Penjualan.objects.get(Q(nota=nota) & Q(cabang=request.user.userprofile.cabang))
        penjualan_detail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
        context = {
            'penjualan':penjualan,
            'penjualan_detail':penjualan_detail
        }
        return render(request,'detail-histori-penjualan.html',context)
    except Exception as ex:
        print(ex)
        return HttpResponse("<center><h4 style='margin-top:200px;font-style:italic'>Maaf tidak memiliki akses.</h4></center>")
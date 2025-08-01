from django.shortcuts import render, HttpResponseRedirect
from .models import Penjualan, PenjualanDetail
from stock.models import Barang, Cabang, DaftarPaket
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.conf import settings
import datetime
from django.contrib.auth import authenticate,login,logout
from cms.views import addLog
from promo.models import Promo
from cara.models import Tutorial,TutorialComment,TutorialImage
from cms.models import Testimoni

DAFTAR_PAKET = []

def cek_expired_kuota(id_cabang):
    cabang = Cabang.objects.get(id=id_cabang)
    try:
        if cabang.lisensi_expired<datetime.datetime.now():
            if cabang.lisensi_grace<datetime.datetime.now():
                return False
            else:
                if cabang.kuota_transaksi>0:
                    return True
                else:
                    return False
        else:
            if cabang.kuota_transaksi>0:
                return True
            else:
                return False
    except:
        return False
    
def cek_kuota_transaksi(id_cabang):
    cabang = Cabang.objects.get(id=id_cabang)
    if cabang.kuota_transaksi>0:
        return True
    else:
        return False

def cek_lisensi_expired(id_cabang):
    try:
        cabang = Cabang.objects.get(id=id_cabang)
        if cabang.lisensi_expired<datetime.datetime.now():
            return False
        else:
            return True
    except:
        return False

def cek_jumlah_grace(id_cabang):
    try:
        cabang = Cabang.objects.get(id=id_cabang)
        return (cabang.lisensi_grace-datetime.datetime.now()).days
    except:
        return 0

def index(request):
    toko = None
    tanggal = datetime.datetime.now()
    cabang_available=False
    jumlah_grace = 0
    jumlah_transaksi=0
    bisa_transaksi=False
    tutorial = Tutorial.objects.all()[:3]
    image = []
    tutorialimage = TutorialImage.objects.all().filter(tutorial__in=tutorial)
    
    # print(dict(tutorial))
    for tutor in tutorial:
        print(type(tutor))
        for imagenya in tutorialimage:
            if(imagenya.tutorial==tutor):
                data = {
                    'tutorial':tutor,
                    'image':imagenya.image
                }
                
                break
        comment = TutorialComment.objects.all().filter(tutorial=tutor).count()
        data['comment']=comment
        image.append(data)
    
    try:
        limapenjualan = Penjualan.objects.all().filter(Q(user=request.user) & Q(is_paid=True)).order_by('-tgl_bayar')[:5]
    except:
        limapenjualan = None

    if request.user.is_authenticated:
        jumlah_transaksi = request.user.userprofile.cabang.kuota_transaksi
        cabang_available = cek_expired_kuota(request.user.userprofile.cabang.id)
        print(cabang_available)
        bisa_transaksi=cek_expired_kuota(request.user.userprofile.cabang.id)
        print(bisa_transaksi)
        jumlah_grace=cek_jumlah_grace(request.user.userprofile.cabang.id)
        print(jumlah_grace)
        user = User.objects.get(username=request.user.username)
        toko = request.user.userprofile.cabang.nama_toko
        if request.method=="POST":
            try:
                nota = request.GET['nota']
            except:
                nota=""

            kode = request.POST['kode']
            print(kode)
                
            if nota != "":
                penjualan= Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
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
                    barang = Barang.objects.get(Q(barcode=kode) & Q(cabang=request.user.userprofile.cabang))
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
                    
                    return HttpResponseRedirect(f'/?nota={nota}')
                else:
                    messages.add_message(request,messages.SUCCESS,"Maaf barang dengan kode tersebut belum ada.")    
            except Exception as ex:
                if (kode):
                    messages.add_message(request,messages.SUCCESS,"Maaf barang dengan kode tersebut belum ada.")
                    penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
                    if len(penjualandetail)==0:
                        penjualan.delete()
                        return HttpResponseRedirect('/')
                try:
                    return HttpResponseRedirect(f'/?nota={nota}')
                except:
                    messages.add_message(request,messages.SUCCESS,"Silakan login untuk bisa melakukan transaksi.")
                    return HttpResponseRedirect('/')
    else:
        user=None

    promo_list = Promo.objects.all().filter(Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gt=0))

    try:
        if request.method != "POST":
            print('ini bukan post')
            # diubah supaya bs fleksible
            try:
                nota = request.GET['nota']
            except:
                nota=""
        else:
            print('ini post')
            print(f'nota: {nota}')
        
        if(nota!=""):
            penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
            penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
            total = int(penjualan.total)
            jumlah_item = penjualan.items
        else:
            penjualandetail=None
            total=0
            jumlah_item=0
    except Exception as ex:
        return HttpResponseRedirect('/')
    try:
        barang = Barang.objects.all().filter(cabang=request.user.userprofile.cabang)
        jml_barang = barang.count()
    except:
        barang = None
        jml_barang=0

    penjualan_pending = Penjualan.objects.all().filter(Q(is_paid=False) & Q(user=user)).order_by('-created_at')
    jumlah_penjualan_pending = penjualan_pending.count()

    bisnis_kecil = DaftarPaket.objects.get(nama="Bisnis Kecil")
    bisnis_medium = DaftarPaket.objects.get(nama="Bisnis Medium")

    testimoni = Testimoni.objects.all().filter(is_verified=True)

    print(f"nota: {nota}")

    context = {
        'penjualandetail':penjualandetail,
        'nota':nota,
        'total':total,
        'jumlah_item':jumlah_item,
        'barang':barang,
        'jml_barang':jml_barang,
        'toko':toko,
        'tanggal':tanggal,
        'penjualan_pending':penjualan_pending,
        'jumlah_penjualan_pending':jumlah_penjualan_pending,
        'bisnis_kecil':bisnis_kecil,
        'bisnis_medium':bisnis_medium,
        'cabang_available':cabang_available,
        'jumlah_grace':jumlah_grace,
        'bisa_transaksi':bisa_transaksi,
        'promo_list':promo_list,
        'jumlah_transaksi':jumlah_transaksi,
        'image_tutorial':image,
        'list_testimoni':testimoni,
        'limapenjualan':limapenjualan
    }
    return render(request,'pos/pos.html',context)

def hapusItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            nota = request.GET['nota']
            id_barang = request.GET['id']
            try:
                penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
                barang = Barang.objects.get(Q(id=int(id_barang)) & Q(cabang=request.user.userprofile.cabang))
                penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang))
                penjualandetail.delete()

                penjualandetail = PenjualanDetail.objects.all().filter(Q(penjualan=penjualan))
                if len(penjualandetail)==0:
                    penjualan.delete()
                    messages.add_message(request,messages.SUCCESS,f'Silakan bertransaksi kembali dengan Tambah Barang.')
                    return HttpResponseRedirect('/')
                else:
                    messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah dihapus.')
                
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(page)    
        except:
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
            return HttpResponseRedirect(page)
    else:
        messages.add_message(request,messages.SUCCESS,'Pengguna telah dinonaktifkan. Silakan menghubungi pemilik toko untuk konfirmasi.')
        return HttpResponseRedirect(page)

def tambahItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            nota = request.GET['nota']
            id_barang = request.GET['id']
            try:
                if nota == "":
                    penjualan = Penjualan()
                else:
                    penjualan = Penjualan.objects.get(nota=nota)
                nota = penjualan.nota
                barang = Barang.objects.get(Q(id=int(id_barang)) & Q(cabang=request.user.userprofile.cabang))
                penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(barang=barang) & Q(is_paid=False))
                penjualandetail.jumlah += 1
                penjualandetail.save()    
                messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah ditambah 1.')
                return HttpResponseRedirect(f"/?nota={nota}")
            except:
                messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            return HttpResponseRedirect(page)    
        except:
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
    else:
        messages.add_message(request,messages.SUCCESS,'Pengguna telah dinonaktifkan. Silakan menghubungi pemilik toko untuk konfirmasi.')
    return HttpResponseRedirect(page)

def ubahItems(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            nota = request.GET['nota']
            id_barang = int(request.GET['id'])
            jumlah = int(request.POST['jumlah'])
            try:
                penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
                barang = Barang.objects.get(Q(id=int(id_barang)) & Q(cabang=request.user.userprofile.cabang))
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
                return HttpResponseRedirect('/')
            return HttpResponseRedirect(page)    
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
    else:
        messages.add_message(request,messages.SUCCESS,'Pengguna telah dinonaktifkan. Silakan menghubungi pemilik toko untuk konfirmasi.')
    return HttpResponseRedirect(page)

def tambahBarang(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"

    if request.user.is_authenticated and request.user.userprofile.is_active:
        user = User.objects.get(username=request.user.username)
        cabang = request.user.userprofile.cabang
        print(cabang.id)
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
                penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
                try:
                    barang = Barang.objects.get(Q(id=int(id_barang)) & Q(cabang = request.user.userprofile.cabang))
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
                return HttpResponseRedirect('/')
            return HttpResponseRedirect(f"?nota={nota}")    
        else:
            penjualan = Penjualan()
            penjualan.cabang=cabang
            penjualan.user=user
            penjualan.save()
            barang = Barang.objects.get(Q(id=int(id_barang)) & Q(cabang=request.user.userprofile.cabang))
            penjualandetail = PenjualanDetail()
            penjualandetail.penjualan=penjualan
            penjualandetail.jumlah=1
            penjualandetail.barang=barang
            penjualandetail.save()
            messages.add_message(request,messages.SUCCESS,f'Jumlah {barang.nama} telah ditambah 1.')
    else:
        messages.add_message(request,messages.SUCCESS,'Pengguna telah dinonaktifkan. Silakan menghubungi pemilik toko untuk konfirmasi.')
    try:
        return HttpResponseRedirect(f"/?nota={penjualan.nota}")
    except:
        return HttpResponseRedirect('/')
    
def hapusTransaksi(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    if request.user.is_authenticated and request.user.userprofile.is_active:
        print('hallo')
        try:
            nota = request.GET['nota']
            try:
                Penjualan.objects.get(Q(nota=nota) & Q(user=request.user) & Q(is_paid=False)).delete()
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
        messages.add_message(request,messages.SUCCESS,'Pengguna telah dinonaktifkan. Silakan menghubungi pemilik toko untuk konfirmasi.')
        return HttpResponseRedirect(page)
        
def loginkan(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        if request.method=="POST":
            username = str(request.POST['username']).lower()
            password = request.POST['password']
            user = authenticate(username=username,password=password)
            if(user):
                if user.userprofile.is_active:
                    login(request,user)
                    messages.add_message(request,messages.SUCCESS,f"Selamat datang {user.userprofile.nama_lengkap}")
                    addLog(user,user.userprofile.cabang,"login",f"login berhasil")
                    return HttpResponseRedirect('/')
                else:
                    messages.add_message(request,messages.SUCCESS,f"Pengguna {user.userprofile.nama_lengkap} telah dinonaktifkan. Silakan menghubungi Pemilik toko untuk konfirmasi.")
                    addLog(user,user.userprofile.cabang,"login",f"pengguna dinonaktifkan, tidak bisa login.")
                    return HttpResponseRedirect('/')
            else:
                # cek di cabang ada atau tidak.
                try:
                    cabang = Cabang.objects.get(email=username)
                    username=f"{cabang.prefix}1"
                    user=authenticate(username=username,password=password)
                    if(user):
                        login(request,user)
                        messages.add_message(request,messages.SUCCESS,f"Selamat datang {user.userprofile.nama_lengkap}")
                        addLog(user,user.userprofile.cabang,"login",f"login berhasil")
                        return HttpResponseRedirect('/')
                except:
                    pass            
                addLog("","","login",f"login dengan user {username} dan password {password} gagal")
                messages.add_message(request,messages.SUCCESS,f"Username dan Password tidak sesuai, silakan ulangi kembali.")
        try:
            toko = request.user.userprofile.cabang.nama_toko
        except:
            toko=""
        context = {
            'toko':toko
        }
        return render(request,'pos/login.html',context)
    
def logoutkan(request):
    try:
        addLog(request.user,request.user.userprofile.cabang,"logout",f"logout berhasil")
        logout(request)
    except:
        pass
    return HttpResponseRedirect('/')

def bayarTransaksi(request):
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            nota = request.GET['nota']
            try:
                penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
                if request.method=="POST":
                    try:
                        no_nota = penjualan.cabang.no_nota
                        penjualan.is_paid=True
                        penjualan.metode=int(request.POST['metode'])
                        penjualan.customer=request.POST['pembeli']
                        penjualan.tgl_bayar = datetime.datetime.now()
                        penjualan.no_nota = str(no_nota).zfill(5)
                        penjualan.user_name = str(request.user.userprofile.nama_lengkap).title()
                        penjualan.save()

                        cabangnya = penjualan.cabang
                        cabangnya.no_nota+=1
                        cabangnya.save()

                        penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
                        for barang in penjualandetail:
                            id_barang = barang.barang.id
                            jumlah=barang.jumlah
                            barangnya = Barang.objects.get(id=id_barang)
                            barangnya.jumlah_dibeli+=jumlah
                            barangnya.stok -= jumlah
                            barangnya.save()
                        addLog(request.user,request.user.userprofile.cabang,"pembayaran",f"Melakukan Pembayaran no. transaksi: {penjualan.nota}")
                        cabang = Cabang.objects.get(id=request.user.userprofile.cabang.id)
                        cabang.kuota_transaksi-=1
                        cabang.save()
                        return HttpResponseRedirect(f'/print/{nota}')
                    except Exception as ex:
                        print(ex)
                        messages.add_message(request,messages.SUCCESS,'Pembayaran Gagal Dilakukan.')
            except Exception as ex:
                # print(ex)
                messages.add_message(request,messages.SUCCESS,"Nomor nota tidak diketemukan.")    
                nota=None
        except Exception as ex:
            # print(ex)
            nota=None
            messages.add_message(request,messages.SUCCESS,"Nomor nota kosong.")
        
        if nota:
            if request.method=="POST":
                print(request.POST)
    else:
        messages.add_message(request,messages.SUCCESS,"Pengguna telah dinonaktifkan dan tidak bisa melakukan transaksi. silakan hubungi Pemilik Toko.")
    return HttpResponseRedirect('/')

def printTransaksi(request,nota):
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            penjualan = Penjualan.objects.get(Q(nota=nota) & Q(user=request.user)  & Q(is_void=False))
            penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
            nama_toko = request.user.userprofile.cabang.nama_toko
            alamat_toko = request.user.userprofile.cabang.alamat_toko
            telpon_toko = request.user.userprofile.cabang.telpon
            total = int(penjualan.total)
            
            if penjualan.metode==0:
                bayar="cash"
            else:
                bayar="transfer"
            context = {
                'penjualan':penjualan,
                'penjualandetail':penjualandetail,
                'nama_toko':nama_toko,
                'alamat_toko':alamat_toko,
                'telpon_toko':telpon_toko,
                'bayar':bayar,
                'total':total
            }
            messages.add_message(request,messages.SUCCESS,"Pembayaran Berhasil.")
            return render(request,'pos/print.html',context)
        except Exception as ex:
            messages.add_message(request,messages.SUCCESS,'Nota yang akan dicetak tidak diketemukan..')
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login untuk bisa mencetak transaksi.")
        return HttpResponseRedirect('/')
    
def gantiStatusOpen(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            try:
                id = request.GET['id']
                nota = request.GET['nota']
                status = int(request.GET['status'])

                penjualandetail = PenjualanDetail.objects.get(id=id)
                if status == 0:
                    penjualandetail.is_open=False
                    messages.add_message(request,messages.SUCCESS,f"Harga barang {penjualandetail.barang.nama} mengunakan metode harga normal kembali.")
                elif status ==1:
                    penjualandetail.is_open=True
                    
                    messages.add_message(request,messages.SUCCESS,f"Harga barang {penjualandetail.barang.nama} mengunakan metode edit harga, dengan minimal harga Rp.1,00.")
                    messages.add_message(request,messages.SUCCESS,"Harga akan update otomatis diupdate oleh sistem 5 Detik setelah Sobat melakukan pengetikan harga. ")
                    messages.add_message(request,messages.SUCCESS,"Untuk mengembalikan ke harga semula silakan tekan tombol refresh berwarna merah di samping. ")
                penjualandetail.save()

                return HttpResponseRedirect(f'/?nota={nota}')
            except:
                return HttpResponseRedirect('/')
        else:
            messages.add_message(request,messages.SUCCESS,"Hanya Admin yang berhak melakukan update harga.")
            return HttpResponseRedirect('/')    
        
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login untuk bisa mencetak transaksi.")
        return HttpResponseRedirect('/')
    

def updateBarangSatuan(request):
    try:
        page=request.META['HTTP_REFERER']
    except:
        page="/"
    
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            nota = request.GET['nota']
            id_barang = int(request.GET['id'])
            update_harga = int(request.GET['harga_baru'])
            if update_harga>0:
                try:
                    penjualan = Penjualan.objects.get(Q(nota=nota) & Q(is_paid=False))
                    penjualandetail = PenjualanDetail.objects.get(Q(penjualan=penjualan) & Q(id=id_barang))
                    harga_awal = penjualandetail.harga
                    penjualandetail.harga = update_harga
                    penjualandetail.save()
                    messages.add_message(request,messages.SUCCESS,f"Harga barang {penjualandetail.barang.nama} sudah diupdate dari harga asli: Rp.{int(harga_awal):,} menjadi harga Rp.{int(update_harga):,}.")
                    messages.add_message(request,messages.SUCCESS,"Untuk mengembalikan ke harga semula silakan tekan tombol refresh berwarna merah di samping.")
                    messages.add_message(request,messages.SUCCESS,"Silakan Sobat Cek terlebih dahulu 1 per 1 harga manual sebelum melakukan pembayaran. Terima kasih.")
                except Exception as ex:
                    print(ex)
                    messages.add_message(request,messages.SUCCESS,'Kode Barang atau Nomor Nota tidak sesuai.')
            else:
                messages.add_message(request,messages.SUCCESS,f'Harga barang tidak boleh nol. silakan cek input Sobat.')
            return HttpResponseRedirect(page)    
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,'Data kode barang atau nota belum dimasukkan.')
            nota = None
            id_barang = None
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan login untuk bisa melakukan transaksi...')
    return HttpResponseRedirect(page)

def reprintTransaksi(request,nota):
    if request.user.is_authenticated  and request.user.userprofile.is_active:
        try:
            penjualan = Penjualan.objects.get(Q(nota=nota) & Q(user=request.user)  & Q(is_void=False))
            penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
            nama_toko = request.user.userprofile.cabang.nama_toko
            alamat_toko = request.user.userprofile.cabang.alamat_toko
            telpon_toko = request.user.userprofile.cabang.telpon
            total = int(penjualan.total)
            penjualan.reprint_nota += 1
            penjualan.save()

            if penjualan.metode==0:
                bayar="cash"
            else:
                bayar="transfer"
            context = {
                'penjualan':penjualan,
                'penjualandetail':penjualandetail,
                'nama_toko':nama_toko,
                'alamat_toko':alamat_toko,
                'telpon_toko':telpon_toko,
                'bayar':bayar,
                'total':total
            }
            return render(request,'pos/reprint.html',context)
        except Exception as ex:
            messages.add_message(request,messages.SUCCESS,'Nota yang akan dicetak tidak diketemukan..')
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login untuk bisa mencetak transaksi.")
        return HttpResponseRedirect('/')
    

def printKuitansi(request,nota):
    if request.user.is_authenticated and request.user.userprofile.is_active:
        try:
            penjualan = Penjualan.objects.get(Q(nota=nota) & Q(user=request.user) & Q(is_void=False))
            penjualandetail = PenjualanDetail.objects.all().filter(penjualan=penjualan)
            nama_toko = request.user.userprofile.cabang.nama_toko
            alamat_toko = request.user.userprofile.cabang.alamat_toko
            telpon_toko = request.user.userprofile.cabang.telpon
            total = int(penjualan.total)
            penjualan.cetak_kuitansi += 1
            penjualan.save()

            id_pemilik = f"{penjualan.cabang.prefix}1"
            nama_pemilik = User.objects.get(username=id_pemilik).userprofile.nama_lengkap

            if penjualan.metode==0:
                bayar="cash"
            else:
                bayar="transfer"
            context = {
                'penjualan':penjualan,
                'penjualandetail':penjualandetail,
                'nama_toko':nama_toko,
                'alamat_toko':alamat_toko,
                'telpon_toko':telpon_toko,
                'bayar':bayar,
                'total':total,
                'nama_pemilik':nama_pemilik
            }
            return render(request,'pos/print_kuitansi.html',context)
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,'Nota yang akan dicetak tidak diketemukan..')
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login untuk bisa mencetak transaksi.")
        return HttpResponseRedirect('/')
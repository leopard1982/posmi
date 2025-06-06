from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.conf import settings
import midtransclient
from stock.models import DaftarPaket,prefixGenerator, Cabang, UserProfile, LogTransaksi
from django.contrib import messages
from django.contrib.auth.models import User
import datetime
from django.db.models import Q
from promo.views import cekKodeToko,cekKodeVoucher
from promo.models import Promo, PromoUsed
from pos.models import DetailWalet
from posmimail import posmiMail

def prosesPayment(noTransaksi,jumlah):
    midtrans_server = settings.MIDTRANS_SERVER
    midtrans_client = settings.MIDTRANS_CLIENT
    midtrans_production = settings.MIDTRANS_PRODUCTION
    params = {
        'transaction_details': {
            'order_id':noTransaksi,
            'gross_amount':jumlah
        },
        'credit_card': {
            'secure':True
        }
    }
    snap = midtransclient.Snap(
        is_production=midtrans_production,
        server_key=midtrans_server,
        client_key=midtrans_client
    )

    transaksi = snap.create_transaction(params)
    return transaksi['redirect_url']

def paymentRequest(request):
    if request.method=="POST":
        paket=""
        harga=None
        kode_toko = prefixGenerator()
        jenis_paket =""
        tipe=None #sm=small, med=medium, tr=trial
        pkt=None #untuk paket, 0 bulanan, 1 3bulan, 2 6bulan, 3 tahunan, 4 2tahunan, 5 trial
        if 'bisnis_kecil' in request.POST:
            tipe="sm"
            paket="PAKET BISNIS KECIL"
            paketan = request.POST['bisnis_kecil']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
                jenis_paket=f"1 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')}"
                pkt=0
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
                jenis_paket=f"3 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=13)).strftime('%d-%m-%Y')}"
                pkt=1
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
                jenis_paket=f"6 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=26)).strftime('%d-%m-%Y')}"
                pkt=2
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
                jenis_paket=f"Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=52)).strftime('%d-%m-%Y')}"
                pkt=3
            else:
                harga = daftarpaket.harga_per_dua_tahun
                jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=104)).strftime('%d-%m-%Y')}"
                pkt=4
        elif 'bisnis_medium' in request.POST:
            paket="PAKET BISNIS MEDIUM"
            paketan = request.POST['bisnis_medium']
            daftarpaket = DaftarPaket.objects.get(nama="Bisnis Medium")
            tipe="med"
            if paketan=="bulanan":
                harga = daftarpaket.harga_per_bulan
                jenis_paket=f"1 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')}"
                pkt=0
            elif paketan=="3bulanan":
                harga = daftarpaket.harga_per_tiga_bulan
                jenis_paket=f"3 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=13)).strftime('%d-%m-%Y')}"
                pkt=1
            elif paketan=="6bulanan":
                harga = daftarpaket.harga_per_enam_bulan
                jenis_paket=f"6 Bulan mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=26)).strftime('%d-%m-%Y')}"
                pkt=2
            elif paketan=="tahunan":
                harga = daftarpaket.harga_per_tahun
                jenis_paket=f"Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=52)).strftime('%d-%m-%Y')}"
                pkt=3
            else:
                harga = daftarpaket.harga_per_dua_tahun
                jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(weeks=104)).strftime('%d-%m-%Y')}"
                pkt=4
        else:
            tipe="tr"
            pkt=0
            paket="PAKET DASAR"
            harga=0
            jenis_paket=f"2 Tahun mulai tanggal {datetime.datetime.now().strftime('%d-%m-%Y')} s.d. {(datetime.datetime.now()+datetime.timedelta(days=7)).strftime('%d-%m-%Y')}"


        context = {
            'paket':paket,
            'harga':harga,
            'kode_toko':kode_toko,
            'jenis_paket':jenis_paket,
            'tipe':tipe,
            'pkt':pkt
        }
        if (tipe == "tr"):
            return render(request,'registrasi/registrasi.html',context)
        else:
            return render(request,'registrasi/registrasi_bayar.html',context)
    return HttpResponseRedirect('/')

def paymentResponse(request):
    try:
        asal = request.META['HTTP_REFERER']
    except:
        asal="/"

    pkt=int(request.GET['pkt'])
    tipe=request.GET['tipe']
    jumlah_transaksi=0
    lisensi_grace=None
    lisensi_expired=None
    kode_referal = None
    harga = 0
    cabang_penerima = None

    print(pkt)
    if pkt==0:
        print('pkt0')
        if(tipe!="tr"):
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=30)
            lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
            if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_bulan
            elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_bulan
        else:
            lisensi_expired = datetime.datetime.now() + datetime.timedelta(days=7)
            lisensi_grace = lisensi_expired
    elif pkt==1:
        print('pkt1')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=13)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_tiga_bulan
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_tiga_bulan
    elif pkt==2:
        print('pkt2')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=26)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_enam_bulan
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_enam_bulan
    elif pkt==3:
        print('pkt3')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=52)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_tahun
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_tahun
    elif pkt==4:
        print('pkt4')
        lisensi_expired = datetime.datetime.now() + datetime.timedelta(weeks=104)
        lisensi_grace = lisensi_expired + datetime.timedelta(days=7)
        if tipe=="sm":
                harga = DaftarPaket.objects.get(nama="Bisnis Kecil").harga_per_dua_tahun
        elif tipe =="med":
                harga = DaftarPaket.objects.get(nama="Bisnis Medium").harga_per_dua_tahun
    if tipe=="tr":
        jumlah_transaksi=100 #default jumlah transaksi adalah 100 kalau trial
        daftarpaket = None
    elif tipe=="sm":
        daftarpaket = DaftarPaket.objects.get(nama="Bisnis Kecil")
        jumlah_transaksi=daftarpaket.max_transaksi
    elif tipe=="med":
        daftarpaket=DaftarPaket.objects.get(nama="Bisnis Medium")
        jumlah_transaksi=daftarpaket.max_transaksi

    

    if request.method=="POST":
        try:
            referensi_cek = cekKodeToko(str(request.POST['referensi']).lower())
        except:
            referensi_cek = False

        try:
            voucher = str(request.POST['voucher']).lower()
            if voucher!="":
                cek_voucher = cekKodeVoucher(kode=voucher,tipe="add")
            else:
                cek_voucher = {
                    'status':False,
                    'disc':0
                }
        except:
            cek_voucher = {
                'status':False,
                'disc':0
            }

        if(cek_voucher['status']):
            try:
                promo = Promo.objects.get(kode=str(request.POST['voucher']).lower())
                harga -= promo.disc
                promo.kuota-=1
                promo.save()
            except:
                pass

            
        if(referensi_cek):
            try:
                # simpan tambahan dana ke wallet
                cabang_penerima = Cabang.objects.get(prefix=str(request.POST['referensi']).lower())
                cabang_penerima.wallet = cabang_penerima.wallet +  int(harga*5/100)
                cabang_penerima.save(force_update=True)
            except:
                pass

        kode_toko = request.POST['kode_toko']
        nama_toko = request.POST['nama_toko']
        nama_cabang = request.POST['nama_cabang']
        alamat_toko = request.POST['alamat_toko']
        telpon_toko = request.POST['telpon_toko']
        email_toko = request.POST['email_toko']
        pemilik_toko = request.POST['pemilik_toko']
        password = request.POST['password_admin']

        try:
            cabang = Cabang.objects.get(email=email_toko)
            messages.add_message(request,messages.SUCCESS,'Pendaftaran Gagal, email sudah pernah teregistrasi. Silakan menggunakan email lain. Terima kasih.')
        except:
            cabang = Cabang()
            cabang.keterangan=""
            cabang.paket=daftarpaket
            cabang.nama_toko=nama_toko
            cabang.nama_cabang=nama_cabang
            cabang.alamat_toko = alamat_toko
            cabang.telpon=telpon_toko
            cabang.email=email_toko
            cabang.prefix=kode_toko
            cabang.lisensi_expired=lisensi_expired
            cabang.lisensi_grace=lisensi_grace
            cabang.kuota_transaksi=jumlah_transaksi
            try:
                cabang.kode_referal = str(request.POST['referensi']).lower()
            except:
                pass
            cabang.no_nota=1
            cabang.save()

            if 'voucher' in request.POST:
                if cek_voucher['status']:
                    promoused = PromoUsed()
                    promoused.promo=promo
                    promoused.cabang=cabang
                    promoused.save()

                detailwallet = DetailWalet()
                detailwallet.cabang=cabang_penerima
                detailwallet.cabang_referensi=cabang
                detailwallet.jumlah=int(harga*5/100)
                detailwallet.keterangan="registrasi toko"
                detailwallet.save()

            print(cabang)

            user = User()
            user.username=f"{kode_toko}1"
            user.email=email_toko
            user.first_name=pemilik_toko
            user.is_active=True
            user.is_superuser=True
            user.password=password
            user.save()
            user.set_password(password)
            user.save()

            userprofile = UserProfile()
            userprofile.user=user
            userprofile.cabang=cabang
            userprofile.nama_lengkap=pemilik_toko
            userprofile.is_active=True
            userprofile.save()

            message = f"Halo Sobat {pemilik_toko}!\n\nSelamat bergabung di aplikasi posmi. Informasi toko sobat adalah sebagai berikut:\nNama Toko: {nama_toko}\nNama Cabang: {cabang}\nAlamat Toko: {alamat_toko}\nKode Toko: {kode_toko}\nEmail Toko: {email_toko}\n\nUntuk user administrator bisa login menggunakan user {user} atau menggunakan email {email_toko}. Password yang telah dibuat adalah [{password}] dan harap disimpan baik-baik.\n\nUntuk login bisa melakukan akses ke: https://posmi.pythonanywhere.com/login/ \n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"

            posmiMail("Terima Kasih Sudah Menggunakan POSMI",message=message,address=email_toko)

            messages.add_message(request,messages.SUCCESS,f"Selamat Untuk User Admin {kode_toko}1 berhasil dibuat. Silakan Login.")

    return HttpResponseRedirect(asal)

def getAdmin(kode_toko):
    try:
        user = User.objects.get(username=f"{kode_toko}1")
        userprofile = UserProfile.objects.get(user=user).nama_lengkap
        return userprofile
    except:
        return ""

def cekLisensi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"
    
    try:
        kode_toko = request.POST['id']
        tipe = request.GET['tipe']    
        info_registrasi=""
        list_kuota=[data for data in range(50,1500,50)]
        list_biaya = []
        try:
            cabang = Cabang.objects.get(prefix=kode_toko)
            if tipe=="small":
                info_registrasi="Perpanjangan Lisensi Bisnis Kecil"
            elif tipe=="medium":
                info_registrasi="Perpanjangan Lisensi Bisnis Kecil"
            elif tipe=="upgrade":
                if cabang.paket== None:
                    info_registrasi="Upgrade ke Paket Bisnis Kecil atau Medium"
                    daftarpaket = DaftarPaket.objects.all().filter(nama__in=['Bisnis Kecil','Bisnis Medium'])
                    sisa_uang=0
                    for daftar in daftarpaket:
                        data = {
                                "id":daftar.paket,
                                'nama':daftar.nama,
                            }
                        biaya_list=[]
                        if int(daftar.harga_per_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'bulanan',
                                'info': '1 bulanan',
                                'data':int(daftar.harga_per_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tiga_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tigabulanan',
                                'info':'3 bulanan',
                                'data':int(daftar.harga_per_tiga_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_enam_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'enambulanan',
                                'info':'6 bulanan',
                                'data':int(daftar.harga_per_enam_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tahunan',
                                'info':'1 tahunan',
                                'data':int(daftar.harga_per_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_dua_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'duatahunan',
                                'info':'2 tahunan',
                                'data':int(daftar.harga_per_dua_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        data['biaya']=biaya_list
                        list_biaya.append(data)
                    print(list_biaya)
                elif cabang.paket.nama=="Bisnis Kecil":
                    info_registrasi="Upgrade ke Paket Bisnis Medium"
                    daftarpaket = DaftarPaket.objects.all().filter(nama__in=['Bisnis Medium'])
                    sisa_hari = int((cabang.lisensi_expired-datetime.datetime.now()).days)
                    sisa_uang = 0
                    # cek apakah sisa hari masih bulanan?
                    sisa_uang = (cabang.paket.harga_per_tahun/365)*sisa_hari
                    for daftar in daftarpaket:
                        data = {
                                "id":str(daftar.paket),
                                'nama':daftar.nama,
                        }
                        
                        biaya_list=[]
                        if int(daftar.harga_per_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'bulanan',
                                'info': '1 bulanan',
                                'data':int(daftar.harga_per_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tiga_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tigabulanan',
                                'info':'3 bulanan',
                                'data':int(daftar.harga_per_tiga_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_enam_bulan-sisa_uang)>0:
                            biaya_data = {
                                'nama':'enambulanan',
                                'info':'6 bulanan',
                                'data':int(daftar.harga_per_enam_bulan-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'tahunan',
                                'info':'1 tahunan',
                                'data':int(daftar.harga_per_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        if int(daftar.harga_per_dua_tahun-sisa_uang)>0:
                            biaya_data = {
                                'nama':'duatahunan',
                                'info':'2 tahunan',
                                'data':int(daftar.harga_per_dua_tahun-sisa_uang)
                            }
                            biaya_list.append(biaya_data)
                        data['biaya']=biaya_list
                        print(data)
                        list_biaya.append(data)
                else:
                    messages.add_message(request,messages.SUCCESS,f"Paket untuk {cabang.nama_toko} sudah Medium tidak bisa melakukan upgrade. Yang bisa dilakukan adalah menambah kuota transaksi penjualan. Terima kasih.")
                    return HttpResponseRedirect('/')
            elif tipe=="kuota":
                info_registrasi="Penambahan Kuota"
            
            nama_admin = getAdmin(kode_toko)
            context = {
                'kode_toko':kode_toko,
                'cabang':cabang,
                'nama_admin':nama_admin,
                'info_registrasi':info_registrasi,
                'tipe':tipe,
                'list_kuota':list_kuota,
                'asal':asal,
                'list_biaya':list_biaya
            }
            return render(request,'registrasi/cek_lisensi.html',context)
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,"Kode Toko Tidak Ditemukan.")    
            if tipe=="small":
                return HttpResponseRedirect("/#lisensismall")
            elif tipe=="medium":
                return HttpResponseRedirect("/#lisensimedium")
            elif tipe=="upgrade":
                return HttpResponseRedirect("/#upgradepaket")
            elif tipe=="kuota":
                return HttpResponseRedirect("/#tambahkuota")
        
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,"Kode Toko Tidak Ditemukan.")
        return HttpResponseRedirect("/")
    
def hitungBiayaKuota(request):
    try:
        jumlah_kuota = int(request.GET['jumlah_kuota'])
        return HttpResponse(f'<span style="width:270px">Perkiraan Biaya adalah:</span> Rp.{int(jumlah_kuota*10000/50):,}.00')
    except:
        return HttpResponse('<span style="width:270px">Perkiraan Biaya adalah:</span> Rp.0.00')

def tambahKuota(request):
    import datetime
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"

    try:
        try:
            voucher = request.POST['voucher']
        except:
            voucher=""
        kode_toko=request.GET['id']
        disc = 0
        
        if voucher!="":
            cek_voucher = cekKodeVoucher(kode=voucher,toko=kode_toko,tipe="add")
        else:
            cek_voucher = {
                'status':False,
                'disc':0
            }
        jumlah_kuota = request.POST['jumlah_kuota']

        cabang = Cabang.objects.get(prefix=kode_toko)

        harga=int(jumlah_kuota)*10000/50
        disc=0

        if cek_voucher['status']:
            print('ok')
            # voucher masih bisa
            disc=cek_voucher['disc']

            # cek harga
            harga = harga-disc
            if harga<0:
                harga=1000

        # hitung wallet bonus
        walet = int(harga*5/100)
                
        try:
                    # update data voucher berkurang 1
                    promo = Promo.objects.get(kode=voucher)
                    promo.kuota -= 1
                    promo.save()

                    # simpan siapa pemakai voucher
                    promoused = PromoUsed()
                    promoused.cabang=cabang
                    promoused.promo=promo
                    promoused.save()
        except Exception as ex:
                    print(ex)


        # simpan tambahan wallet untuk referal (kalau ada)
        try:
                    print(f'penambahan wallet di cabang {cabang.nama_cabang} dengan kode referal {cabang.kode_referal}')
                    kode_ref = cabang.kode_referal
                    reff = Cabang.objects.get(prefix=kode_ref)
                    reff.wallet = reff.wallet+walet
                    reff.save()

                    print('sekarang menambahkan detail wallet')
                    detailwallet = DetailWalet()
                    detailwallet.cabang=reff
                    detailwallet.cabang_referensi=cabang
                    detailwallet.jumlah=walet
                    detailwallet.keterangan="penambahan kuota transaksi"
                    detailwallet.save()
                    print('detail wallet sudah ditambahkan')
        except Exception as ex:
                    print(ex)

        jumlah_kuota = request.POST['jumlah_kuota']
        cabang.kuota_transaksi+=int(jumlah_kuota)
        cabang.save()

        user = User.objects.get(username=f"{cabang.prefix}1")
        userprofile = UserProfile.objects.get(user=user)

        message = f"Halo Sobat {userprofile.nama_lengkap}!\n\nTerima kasih atas pembelian {int(jumlah_kuota):,} kuota transaksi dengan pembayaran sebesar: Rp.{int(harga):,} pada tanggal: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n\nTerima kasih sudah memilih POSMI sebagai aplikasi untuk penjualan di toko Sobat. Apabila ada kendala segera hubungi tim POSMI.\n\n\nSalam,\n\nSuryo Adhy Chandra\n------------------\nCreator POSMI\n\n\nEmail: adhy.chandra@live.co.uk\nWhatsapp: +6281213270275\nTelegram: @suryo_adhy"

        posmiMail("Terima Kasih Sudah Menggunakan POSMI",message=message,address=cabang.email)

        logtransaksi = LogTransaksi()
        logtransaksi.cabang=cabang
        logtransaksi.keterangan=f"pembelian kuota {jumlah_kuota}"
        logtransaksi.transaksi="kuota transaksi"
        logtransaksi.save()
        
        messages.add_message(request,messages.SUCCESS,f"Selamat kuota transaksi untuk toko {cabang.nama_toko} ({cabang.nama_cabang}) telah bertambah {jumlah_kuota} menjadi sebanyak: {cabang.kuota_transaksi} transaksi. ")
        return HttpResponseRedirect('/')
    except Exception as ex:
        print(ex)
        return HttpResponseRedirect(asal)
    
def hitungExpired(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"
    try:
        kode_toko = request.GET['id']
        cabang = Cabang.objects.get(prefix=kode_toko)
        metode = str(request.GET['list_biaya']).split('^')[0]
        if(metode==""):
            return HttpResponse("")
        tanggal_expired = None
        day=0
        if metode=="bulanan":
            day = 30
        elif metode=="tigabulanan":
            day = 30*3
        elif metode=="enambulanan":
            day = 30*6
        elif metode=="tahunan":
            day = 365
        elif metode=="duatahunan":
            day = 365*2
        
        try:
            sisa_hari = (cabang.lisensi_expired-datetime.datetime.now()).days
        except:
            sisa_hari=0
            day = day-sisa_hari
        try:
            if cabang.lisensi_expired< datetime.datetime.now():
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
            else:
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired = tanggal_expired + datetime.timedelta(days=day)
        except:
            tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        return HttpResponse(f"Lisensi akan berakhir: {tanggal_expired.strftime("%d/%m/%Y")}")
    except Exception as ex:
        print(ex)
        return HttpResponse("-")
    
def upgradeLisensi(request):
    try:
        asal = request.META['HTTP_REFERER']
    except Exception as ex:
        print(ex)
        asal="/"

    try:
        print(request.GET)
        print(request.POST)
        kode_toko=request.GET['id']
        print(kode_toko)
        cabang = Cabang.objects.get(prefix=kode_toko)
        metode = str(request.POST['list_biaya']).split('^')[0]
        paket_id = str(request.POST['list_biaya']).split('^')[1]
        paket = DaftarPaket.objects.get(paket=paket_id)
        if metode=="bulanan":
            day = 30
        elif metode=="tigabulanan":
            day = 30*3
        elif metode=="enambulanan":
            day = 30*6
        elif metode=="tahunan":
            day = 365
        elif metode=="duatahunan":
            day = 365*2

        try:
            sisa_hari = (cabang.lisensi_expired-datetime.datetime.now()).days
        except:
            sisa_hari=0
            day = day-sisa_hari

        try:
            if cabang.lisensi_expired< datetime.datetime.now():
                tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
            else:
                # day = day-(cabang.lisensi_expired-datetime.datetime.now()).days
                tanggal_expired = tanggal_expired + datetime.timedelta(days=day)
        except:
            tanggal_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        
        # try:
        #     day =  day-(cabang.lisensi_expired-datetime.datetime.now()).days
        # except:
        #     pass
            
        # print(cabang)
        # if cabang.lisensi_expired==None:
        #     cabang.lisensi_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        # else:
        #     if(cabang.lisensi_expired<datetime.datetime.now()):
        #         cabang.lisensi_expired=datetime.datetime.now() + datetime.timedelta(days=day)
        #     else:
        #         cabang.lisensi_expired = cabang.lisensi_expired + datetime.timedelta(days=day)
        cabang.lisensi_expired=tanggal_expired
        cabang.lisensi_grace = tanggal_expired + datetime.timedelta(days=7)
        cabang.kuota_transaksi+=paket.max_transaksi
        cabang.paket=paket
        cabang.save()
        messages.add_message(request,messages.SUCCESS,f"Selamat untuk toko {cabang.nama_toko} ({cabang.nama_cabang}) telah menggunakan paket {paket.nama} dengan lisensi diperpanjang sampai dengan {cabang.lisensi_expired.strftime("%d/%m/%Y")}.")
        return HttpResponseRedirect('/')
    except Exception as ex:
        print(ex)
        return HttpResponseRedirect(asal)
    

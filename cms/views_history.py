from pos.models import Penjualan,PenjualanDetail
from django.contrib import messages
from django.shortcuts import HttpResponse,HttpResponseRedirect,render
from django.http.response import FileResponse
import uuid
import datetime
from django.db.models import Q

def getHistoryBB(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            try:
                print(f"request.get: {request.GET}")
                bulan=int(request.GET['bulan'])
                tahun=int(request.GET['tahun'])
                try:
                    filternya = int(request.GET['f'])
                    if filternya<0 or filternya>2:
                        filternya=0
                except:
                    filternya = 0
                nama_file = 'download_history/' + str(uuid.uuid4()) + ".csv"
                file = open(nama_file,'w')
                file.write('no,id_transaksi,nomor_nota,cabang,user_id,user_name,total_item,total_bayar,metode_bayar,tanggal,customer,nota_print,kuitansi_print,status,alasan_void\n')

                if filternya == 0:
                    penjualan = Penjualan.objects.all().filter(Q(cabang=request.user.userprofile.cabang) & Q(tgl_bayar__month=bulan) & Q(tgl_bayar__year=tahun))
                elif filternya == 1:
                    # transaksi sukses
                    penjualan = Penjualan.objects.all().filter(Q(cabang=request.user.userprofile.cabang) & Q(tgl_bayar__month=bulan) & Q(tgl_bayar__year=tahun) & Q(is_void=False))
                elif filternya == 2:
                    # transaksi gagal
                    penjualan = Penjualan.objects.all().filter(Q(cabang=request.user.userprofile.cabang) & Q(tgl_bayar__month=bulan) & Q(tgl_bayar__year=tahun) & Q(is_void=True))
                
                index=1
                for jual in penjualan:
                    if jual.is_void:
                        alasan_void=jual.alasan_void
                        status = "Batal (VOID)"
                    else:
                        alasan_void="-"
                        status = "Sukses"
                    file.write(f"{index},{jual.nota},{int(jual.no_nota):05d},{jual.cabang.prefix},{jual.user.username},{jual.user.userprofile.nama_lengkap},{jual.items},{jual.total},{jual.metode},{jual.tgl_bayar.strftime('%d/%h/%Y %H:%M:%Y')},{jual.customer},{jual.reprint_nota},{jual.cetak_kuitansi},{status},{alasan_void}\n")
                    index +=1
                file.close()
                
                file=open(nama_file,'rb')
                file_response = FileResponse(file,as_attachment=True,filename=f"histori_{request.user.userprofile.cabang.prefix}_{bulan}_{tahun}.csv")
                return file_response
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
                return HttpResponseRedirect('/cms/')

            
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.conf import settings
import midtransclient

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
    # snap = midtransclient.Snap(
    #     is_production=midtrans_production,
    #     server_key=midtrans_server,
    #     client_key=midtrans_client
    # )

    # transaksi = snap.create_transaction(params)
    # return transaksi['redirect_url']
    return True

def paymentRequest(request):
    return HttpResponseRedirect('/')

def paymentResponse(request):
    return HttpResponse(request.GET)


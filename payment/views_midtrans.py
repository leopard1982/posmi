import midtransclient
import os
from django.conf import settings
from django.shortcuts import HttpResponse,render

def paymentMidtrans(order_id):
    jumlah = 200000
    snap = midtransclient.Snap(
        is_production=False,
        server_key=settings.MIDTRANS_SERVER,
        client_key=settings.MIDTRANS_CLIENT
    )

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": jumlah,
        },
        "credit_card": {
            "secure": True
        }
    }
    try:
        transaction = snap.create_transaction(parameters=param)
    except Exception as ex:
        print(ex)
        transaction = None
    return transaction

def responseMidtransPayment(request):
    print(f"post: {request.POST}")
    print(f"get: {request.GET}")
    return HttpResponse('ok')
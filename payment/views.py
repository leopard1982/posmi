from django.shortcuts import render, HttpResponseRedirect

def paymentRequest(request):
    return HttpResponseRedirect('/')

def paymentResponse(request):
    print(request.GET)
    return HttpResponseRedirect('/')
from django.shortcuts import render, HttpResponseRedirect, HttpResponse

def paymentRequest(request):
    return HttpResponseRedirect('/')

def paymentResponse(request):
    return HttpResponse(request.GET)
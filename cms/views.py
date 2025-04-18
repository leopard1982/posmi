from django.shortcuts import render, HttpResponseRedirect, HttpResponse
from django.contrib import messages

# Create your views here.
def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return render(request,'administrator/index.html')
        else:
            messages.add_message(request,messages.SUCCESS,"Anda tidak memiliki ijin untuk mengkases halaman admin posmi.")
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,"Silakan Login terlebih dahulu untuk bisa mengakses halaman admin posmi.")
        return HttpResponseRedirect('/login/')
from django.shortcuts import render, HttpResponse
# from .models import Promo
from django.db.models import Q
import datetime

# Create your views here.
# def getPromo(request):
#     promo_list = Promo.objects.all().filter(Q(end_period__gte=datetime.datetime.now()) & Q(is_active=True) & Q(kuota__gt=0))
#     context = {
#         'promo_list':promo_list
#     }
#     return render(request,'promo/list_promo.html',context)
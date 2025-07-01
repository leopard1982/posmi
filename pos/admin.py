from django.contrib import admin
from .models import Penjualan, PenjualanDetail, TotalPenjualan
# Register your models here.

admin.site.register(Penjualan)
admin.site.register(PenjualanDetail)
admin.site.register(TotalPenjualan)
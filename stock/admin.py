from django.contrib import admin
from .models import Barang, Cabang, Customer, UserProfile
# Register your models here.

admin.site.register(Barang)
admin.site.register(Cabang)
admin.site.register(Customer)
admin.site.register(UserProfile)
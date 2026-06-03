from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='management_index'),
    path('paket/', views.paket_list, name='management_paket'),
    path('promo/', views.promo_list, name='management_promo'),
    path('testimoni/', views.testimoni_list, name='management_testimoni'),
    path('cabang/', views.cabang_list, name='management_cabang'),
    path('users/', views.user_list, name='management_users'),
    path('pembelian/', views.pembelian_list, name='management_pembelian'),
]

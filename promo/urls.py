from django.urls import path
from .views import getPromo

urlpatterns = [
    path('',getPromo,name="get_promo"),
]

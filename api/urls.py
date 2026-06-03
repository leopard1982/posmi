from django.urls import path
from . import views

urlpatterns = [
    path('v1/info/',         views.api_info,         name='api_info'),
    path('v1/transactions/', views.api_transactions,  name='api_transactions'),
    path('v1/products/',     views.api_products,      name='api_products'),
    path('v1/stock/',        views.api_stock,         name='api_stock'),
    path('v1/webhooks/',     views.api_webhooks,      name='api_webhooks'),
]

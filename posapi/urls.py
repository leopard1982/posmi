from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/',   views.LoginView.as_view()),
    path('auth/refresh/', views.RefreshView.as_view()),
    path('auth/logout/',  views.LogoutView.as_view()),
    path('me/',           views.MeView.as_view()),
    path('products/',     views.ProductListView.as_view()),
    path('products/barcode/<str:kode>/', views.ProductByBarcodeView.as_view()),
    path('sales/checkout/', views.CheckoutView.as_view()),
    path('sales/',        views.SaleListView.as_view()),
    path('sales/<uuid:nota>/',         views.SaleDetailView.as_view()),
    path('sales/<uuid:nota>/reprint/', views.SaleReprintView.as_view()),
]

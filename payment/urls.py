from django.urls import path
from .views import paymentRequest, paymentResponse

urlpatterns = [
    path('req/',paymentRequest,name='payment_request' ),
    path('res/',paymentResponse,name='payment_response')
]

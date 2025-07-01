from django.urls import path
from .views import index_cara,detailCara

urlpatterns = [
    path('',index_cara,name="index_cara"),
    path('detail/<str:id>/',detailCara,name="detail_cara")
]

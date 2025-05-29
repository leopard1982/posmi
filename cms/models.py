from django.db import models
from stock.models import Cabang
import uuid

# Create your models here.
class Testimoni(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,primary_key=True,default=uuid.uuid4)
    cabang = models.OneToOneField(Cabang,on_delete=models.RESTRICT,null=True,blank=True)
    testimoni = models.CharField(max_length=200,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True,null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.cabang}] {self.testimoni}"
from django.db import models
from stock.models import Cabang
import uuid
import datetime
from django.contrib.auth.models import User

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
    

class GantiEmail(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,primary_key=True,default=uuid.uuid4)
    expired = models.DateTimeField(blank=True,null=True)
    clicked = models.BooleanField(default=False)
    cabang = models.ForeignKey(Cabang,on_delete=models.DO_NOTHING,related_name="cabang_konfirmasi",blank=True,null=True)
    email_baru = models.CharField(max_length=200,blank=True,null=True)
    user = models.ForeignKey(User,on_delete=models.DO_NOTHING,related_name="user_konfirmasi",blank=True,null=True)

    def save(self,*args,**kwargs):
        self.expired = datetime.datetime.now() + datetime.timedelta(hours=1)
        super(GantiEmail,self).save(*args,**kwargs)
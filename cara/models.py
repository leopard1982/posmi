from django.db import models
import uuid

# Create your models here.
class Tutorial(models.Model):
    id = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4,primary_key=True)
    judul = models.CharField(max_length=100,default="")
    artikel = models.TextField()
    created_at =models.DateTimeField(auto_now_add=True)
    view = models.IntegerField(default=0)
    created_by= models.CharField(default="",max_length=100)

    def __str__(self):
        return self.judul

class TutorialComment(models.Model):
    tutorial = models.ForeignKey(Tutorial,on_delete=models.RESTRICT,null=True,blank=True)
    comment = models.CharField(max_length=200,default="")
    is_publish = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(default="",max_length=100)
    email_creator = models.EmailField(max_length=200,default="")

    def __str__(self):
        return f"{self.tutorial.judul} - {self.comment}"

class TutorialImage(models.Model):
    tutorial = models.ForeignKey(Tutorial,on_delete=models.RESTRICT,null=True,blank=True)
    image = models.ImageField(upload_to="tutorial_image",blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tutorial.judul
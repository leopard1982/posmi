from django.shortcuts import render
from .models import Tutorial,TutorialImage,TutorialComment

# Create your views here.
def index_cara(request):
    return render(request,'blogs/list_blogs.html')

def detailCara(request,id):
    id = id
    tutorial = Tutorial.objects.get(id=id)
    images = TutorialImage.objects.all().filter(tutorial=tutorial).order_by('created_at')
    context = {
        'tutorial':tutorial,
        'images':images
    }
    return render(request,'blogs/detail_blogs.html',context)
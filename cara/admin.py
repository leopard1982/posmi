from django.contrib import admin
from .models import Tutorial,TutorialComment,TutorialImage


admin.site.register(Tutorial)
admin.site.register(TutorialComment)
admin.site.register(TutorialImage)
from django import forms
from stock.models import UploadBarang

class FormUploadBarang(forms.ModelForm):
    class Meta:
        model = UploadBarang
        fields = ['file']

        widgets = {
            'file': forms.FileField(
                attrs= {
                    'class':'form-control'
                }
            )
        }
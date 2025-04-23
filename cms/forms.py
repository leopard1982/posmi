from django import forms
from stock.models import UploadBarang, Cabang

class FormUploadBarang(forms.ModelForm):
    class Meta:
        model = UploadBarang
        fields = ['file']

class FormInfoToko(forms.ModelForm):
    class Meta:
        model = Cabang
        fields = ['nama_toko','nama_cabang','alamat_toko','telpon','keterangan']

        widgets = {
            'nama_toko': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Nama Toko",
                    'max_length':20,
                    'required':'required'
                }
            ),
            'nama_cabang': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Nama Cabang",
                    'max_length':15,
                    'required':'required'
                }
            ),
            'alamat_toko': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Nama Alamat Toko",
                    'max_length':30,
                    'required':'required'
                }
            ),
            'telpon': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Nomor Telpon",
                    'max_length':15,
                    'required':'required'
                }
            ),
            'keterangan': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Keterangan",
                    'max_length':200,
                }
            ),
        }




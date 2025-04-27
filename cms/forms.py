from django import forms
from stock.models import UploadBarang, Cabang, UserProfile,Barang
from django.contrib.auth.models import User

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

class FormUser(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username','email']

class FormUserProfile(forms.ModelForm):
    user = FormUser
    class Meta:
        model = UserProfile
        fields = "__all__"

class FormBarang(forms.ModelForm):
    class Meta:
        model = Barang
        fields = ['barcode','nama','satuan','stok','harga_ecer','harga_grosir','min_beli_grosir','jumlah_dibeli']

        widgets = {
            'barcode': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Kode Barcode",
                    'max_length':100,
                    'required':'required'
                }
            ),
            'nama': forms.TextInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Nama Barang",
                    'max_length':200,
                    'required':'required'
                }
            ),
            'satuan': forms.Select(
                attrs= {
                    'class':'form-select my-2',
                    'placeholder':"Isi Nama Alamat Toko",
                    'max_length':30,
                    'required':'required'
                }
            ),
            'stok': forms.NumberInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Jumlah Stok",
                    'max_length':15,
                    'required':'required'
                }
            ),
            'harga_ecer': forms.NumberInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Harga Ecer",
                    'max_length':200,
                }
            ),
            'harga_grosir': forms.NumberInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Harga Grosir",
                    'max_length':200,
                }
            ),
            'min_beli_grosir': forms.NumberInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Jumlah Minimal Grosir",
                    'max_length':200,
                }
            ),
            'jumlah_dibeli': forms.NumberInput(
                attrs= {
                    'class':'form-control my-2',
                    'placeholder':"Isi Harga Ecer",
                    'max_length':200,
                    'readonly':'readonly'
                }
            ),
        }

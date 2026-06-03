from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0006_order_barang'),
        ('stock', '0045_cabang_is_gudang'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestMasterBarang',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('barcode', models.CharField(max_length=100)),
                ('nama', models.CharField(max_length=200)),
                ('satuan', models.CharField(default='PCS', max_length=20)),
                ('harga_beli', models.IntegerField(default=0)),
                ('harga_ecer', models.IntegerField(default=0)),
                ('harga_grosir', models.IntegerField(default=0)),
                ('min_beli_grosir', models.IntegerField(default=0)),
                ('keterangan', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(choices=[('pending','Menunggu Persetujuan'),('conflict','Barcode Konflik'),('approved','Disetujui'),('rejected','Ditolak')], default='pending', max_length=10)),
                ('catatan_toko', models.CharField(blank=True, max_length=200)),
                ('catatan_owner', models.CharField(blank=True, max_length=200)),
                ('barcode_baru', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_master_barang', to='owner.owner')),
                ('cabang', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='request_barang', to='stock.cabang')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0005_pengiriman_gudang'),
        ('stock', '0045_cabang_is_gudang'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderBarang',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('nomor_order', models.CharField(max_length=10, unique=True)),
                ('status', models.CharField(choices=[('pending','Menunggu Persetujuan'),('diproses','Diproses Owner'),('dikirim','Sudah Dikirim'),('ditolak','Ditolak')], default='pending', max_length=10)),
                ('catatan_toko', models.CharField(blank=True, max_length=200)),
                ('catatan_owner', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_masuk', to='owner.owner')),
                ('cabang', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='order_barang', to='stock.cabang')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='OrderBarangItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('barcode', models.CharField(max_length=100)),
                ('nama_barang', models.CharField(blank=True, max_length=200)),
                ('jumlah_order', models.PositiveIntegerField()),
                ('jumlah_disetujui', models.PositiveIntegerField(default=0)),
                ('stok_gudang', models.IntegerField(default=0)),
                ('catatan', models.CharField(blank=True, max_length=200)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_set', to='owner.orderbarang')),
            ],
        ),
    ]

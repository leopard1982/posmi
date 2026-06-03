from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0004_transferstok_nomor_faktur'),
        ('stock', '0045_cabang_is_gudang'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PengirimanGudang',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomor_pengiriman', models.CharField(max_length=10, unique=True)),
                ('status', models.CharField(choices=[('draft','Draft'),('dikirim','Dalam Pengiriman'),('selesai','Selesai'),('sebagian','Selesai (Ada Pengembalian)')], default='dikirim', max_length=10)),
                ('catatan', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengiriman_gudang', to='owner.owner')),
                ('cabang_tujuan', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='penerimaan_gudang', to='stock.cabang')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PengirimanGudangItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jumlah_dikirim', models.PositiveIntegerField()),
                ('jumlah_diterima', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('pending','Menunggu Konfirmasi Toko'),('diterima','Diterima Toko'),('dikembalikan','Dikembalikan (Menunggu Konfirmasi Gudang)'),('kembali_gudang','Kembali ke Gudang')], default='pending', max_length=20)),
                ('catatan_toko', models.CharField(blank=True, max_length=200)),
                ('catatan_gudang', models.CharField(blank=True, max_length=200)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pengiriman', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_set', to='owner.pengirimanGudang')),
                ('barang_gudang', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='pengiriman_item', to='stock.barang')),
            ],
        ),
    ]

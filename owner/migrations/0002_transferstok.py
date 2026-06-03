from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0001_initial'),
        ('stock', '0044_cabang_owner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferStok',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('jumlah', models.PositiveIntegerField()),
                ('catatan', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='owner.owner')),
                ('cabang_asal', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='transfer_keluar', to='stock.cabang')),
                ('cabang_tujuan', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='transfer_masuk', to='stock.cabang')),
                ('barang_asal', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='transfer_dari', to='stock.barang')),
                ('barang_tujuan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='transfer_ke', to='stock.barang')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

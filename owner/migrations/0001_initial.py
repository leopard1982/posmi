from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nama', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('jumlah_slot', models.PositiveIntegerField(default=0)),
                ('kuota_transaksi_pool', models.PositiveIntegerField(default=0)),
                ('lisensi_expired', models.DateTimeField(blank=True, null=True)),
                ('lisensi_grace', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='owner_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

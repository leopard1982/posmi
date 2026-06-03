from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0002_transferstok'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='transferstok',
            name='status',
            field=models.CharField(
                choices=[('pending','Menunggu Persetujuan'),('approved','Disetujui'),('rejected','Ditolak')],
                default='pending', max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='transferstok',
            name='catatan_owner',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='transferstok',
            name='approved_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='transfer_disetujui',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='transferstok',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='transferstok',
            name='created_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='transfer_dibuat',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

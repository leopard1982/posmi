from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0008_penjualan_alasan_void_penjualan_is_void'),
    ]

    operations = [
        migrations.AddField(
            model_name='penjualan',
            name='is_checked',
            field=models.BooleanField(default=False),
        ),
    ]

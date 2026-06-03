from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0009_penjualan_is_checked'),
    ]

    operations = [
        migrations.AddField(
            model_name='penjualan',
            name='jatuh_tempo',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='penjualan',
            name='is_tempo_lunas',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='penjualan',
            name='metode',
            field=models.IntegerField(
                choices=[(0, 'cash'), (1, 'transfer'), (2, 'tempo')],
                default=0,
            ),
        ),
    ]

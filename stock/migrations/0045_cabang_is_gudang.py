from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0044_cabang_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='cabang',
            name='is_gudang',
            field=models.BooleanField(default=False, verbose_name='Gudang Utama'),
        ),
    ]

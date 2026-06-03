from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0045_cabang_is_gudang'),
    ]

    operations = [
        migrations.AddField(
            model_name='cabang',
            name='is_email_verified',
            field=models.BooleanField(default=False, verbose_name='Email Terverifikasi'),
        ),
    ]

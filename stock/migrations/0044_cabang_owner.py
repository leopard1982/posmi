from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0001_initial'),
        ('stock', '0043_alter_cabang_kuota_transaksi'),
    ]

    operations = [
        migrations.AddField(
            model_name='cabang',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cabang_korporasi', to='owner.owner'),
        ),
    ]

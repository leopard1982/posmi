from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('owner', '0003_transferstok_status_approval'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferstok',
            name='nomor_faktur',
            field=models.CharField(blank=True, max_length=10),
        ),
    ]

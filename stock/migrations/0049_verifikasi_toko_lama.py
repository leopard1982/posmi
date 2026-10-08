from django.db import migrations


def tandai_toko_lama_terverifikasi(apps, schema_editor):
    # Alur baru mewajibkan verifikasi email sebelum login; toko yang sudah ada tidak boleh terkunci.
    Cabang = apps.get_model('stock', 'Cabang')
    Cabang.objects.filter(is_email_verified=False).update(is_email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0048_logtransaksi_detail'),
    ]

    operations = [
        migrations.RunPython(tandai_toko_lama_terverifikasi, migrations.RunPython.noop),
    ]

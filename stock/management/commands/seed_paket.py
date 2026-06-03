from django.core.management.base import BaseCommand
from stock.models import DaftarPaket


PAKET_DATA = [
    {
        "nama": "Free",
        "max_transaksi": 50,
        "max_user_login": 1,
        "harga_per_bulan": 0,
        "harga_per_tiga_bulan": 0,
        "harga_per_enam_bulan": 0,
        "harga_per_tahun": 0,
        "harga_per_dua_tahun": 0,
        "disc": 0,
        "is_ceklist_barang": False,
        "is_pembayaran_tempo": False,
        "is_add_ons": False,
    },
    {
        "nama": "Starter",
        "max_transaksi": 200,
        "max_user_login": 2,
        "harga_per_bulan": 49000,
        "harga_per_tiga_bulan": 135000,
        "harga_per_enam_bulan": 255000,
        "harga_per_tahun": 480000,
        "harga_per_dua_tahun": 900000,
        "disc": 0,
        "is_ceklist_barang": False,
        "is_pembayaran_tempo": False,
        "is_add_ons": False,
    },
    {
        "nama": "Bisnis Basic",
        "max_transaksi": 500,
        "max_user_login": 3,
        "harga_per_bulan": 99000,
        "harga_per_tiga_bulan": 275000,
        "harga_per_enam_bulan": 520000,
        "harga_per_tahun": 990000,
        "harga_per_dua_tahun": 1850000,
        "disc": 0,
        "is_ceklist_barang": False,
        "is_pembayaran_tempo": False,
        "is_add_ons": True,
    },
    {
        "nama": "Bisnis Medium",
        "max_transaksi": 1000,
        "max_user_login": 5,
        "harga_per_bulan": 199000,
        "harga_per_tiga_bulan": 550000,
        "harga_per_enam_bulan": 1050000,
        "harga_per_tahun": 1990000,
        "harga_per_dua_tahun": 3700000,
        "disc": 0,
        "is_ceklist_barang": True,
        "is_pembayaran_tempo": True,
        "is_add_ons": True,
    },
    {
        "nama": "Bisnis Pro",
        "max_transaksi": 0,  # 0 = unlimited
        "max_user_login": 10,
        "harga_per_bulan": 299000,
        "harga_per_tiga_bulan": 825000,
        "harga_per_enam_bulan": 1575000,
        "harga_per_tahun": 2990000,
        "harga_per_dua_tahun": 5600000,
        "disc": 0,
        "is_ceklist_barang": True,
        "is_pembayaran_tempo": True,
        "is_add_ons": True,
    },
]


class Command(BaseCommand):
    help = "Seed data DaftarPaket"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus semua paket lama sebelum seed ulang",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            count = DaftarPaket.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Hapus {count} paket lama."))

        created_count = 0
        updated_count = 0

        for data in PAKET_DATA:
            obj, created = DaftarPaket.objects.update_or_create(
                nama=data["nama"],
                defaults={k: v for k, v in data.items() if k != "nama"},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [+] {obj.nama}"))
            else:
                updated_count += 1
                self.stdout.write(f"  [=] {obj.nama} (sudah ada, diupdate)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSelesai: {created_count} dibuat, {updated_count} diupdate."
            )
        )

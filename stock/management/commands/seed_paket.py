from django.core.management.base import BaseCommand
from stock.models import DaftarPaket


PAKET_DATA = [
    {
        "nama": "Kecil",
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
        "nama": "Medium",
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

        existing = set(DaftarPaket.objects.values_list("nama", flat=True))

        for data in PAKET_DATA:
            if data["nama"] in existing:
                updated_count += 1
                self.stdout.write(f"  [=] {data['nama']} (sudah ada, dilewati)")
                continue
            DaftarPaket.objects.create(**data)
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"  [+] {data['nama']}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSelesai: {created_count} dibuat, {updated_count} diupdate."
            )
        )

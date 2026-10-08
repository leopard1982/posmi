from django.core.management.base import BaseCommand
from stock.models import DaftarPaket


def _harga(bulanan):
    # diskon: 3 bln 10%, 6 bln 15%, 1 thn 20%, 2 thn 25%
    return {
        "harga_per_bulan": bulanan,
        "harga_per_tiga_bulan": int(bulanan * 3 * 0.90),
        "harga_per_enam_bulan": int(bulanan * 6 * 0.85),
        "harga_per_tahun": int(bulanan * 12 * 0.80),
        "harga_per_dua_tahun": int(bulanan * 24 * 0.75),
    }


# Nama harus sama persis dengan yang dipakai di cms/views.py & payment/views.py
PAKET_DATA = [
    {
        "nama": "Bisnis Kecil",
        "max_transaksi": 1000,
        "max_user_login": 5,
        **_harga(50000),
        "disc": 0,
        "is_ceklist_barang": False,
        "is_pembayaran_tempo": False,
        "is_add_ons": False,
    },
    {
        "nama": "Bisnis Medium",
        "max_transaksi": 3000,
        "max_user_login": 10,
        **_harga(120000),
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
            defaults = {k: v for k, v in data.items() if k != "nama"}
            _, created = DaftarPaket.objects.update_or_create(
                nama=data["nama"], defaults=defaults
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [+] {data['nama']}"))
            else:
                updated_count += 1
                self.stdout.write(f"  [~] {data['nama']} (diupdate)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSelesai: {created_count} dibuat, {updated_count} diupdate."
            )
        )

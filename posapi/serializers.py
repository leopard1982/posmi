import datetime
from rest_framework import serializers
from stock.models import Barang
from pos.models import Penjualan, PenjualanDetail, METODE_BAYAR

METODE_LABEL = dict(METODE_BAYAR)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class BarangSerializer(serializers.ModelSerializer):
    # harga_beli (modal) sengaja tidak diekspos ke kasir.
    class Meta:
        model = Barang
        fields = ['id', 'barcode', 'nama', 'satuan', 'stok',
                  'harga_ecer', 'harga_grosir', 'min_beli_grosir']


class CheckoutItemSerializer(serializers.Serializer):
    barang_id = serializers.IntegerField(min_value=1)
    jumlah = serializers.IntegerField(min_value=1, max_value=100000)
    # harga manual (opsional) — hanya admin/superuser, divalidasi di view.
    harga = serializers.IntegerField(min_value=1, max_value=2_000_000_000, required=False)


class CheckoutSerializer(serializers.Serializer):
    nota = serializers.UUIDField()  # dibuat client → idempotent saat retry
    items = CheckoutItemSerializer(many=True, allow_empty=False, max_length=200)
    metode = serializers.ChoiceField(choices=[0, 1, 2], default=0)
    pembeli = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    jatuh_tempo = serializers.DateField(required=False)

    def validate_items(self, items):
        ids = [i['barang_id'] for i in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Barang duplikat dalam satu transaksi.')
        return items

    def validate(self, attrs):
        if attrs['metode'] == 2:
            jt = attrs.get('jatuh_tempo')
            if not jt:
                raise serializers.ValidationError({'jatuh_tempo': 'Wajib diisi untuk pembayaran tempo.'})
            if jt < datetime.date.today():
                raise serializers.ValidationError({'jatuh_tempo': 'Tidak boleh sebelum hari ini.'})
        return attrs


def serialize_sale(p, with_items=True):
    data = {
        'nota': str(p.nota),
        'no_nota': p.no_nota,
        'tanggal': (p.tgl_bayar or p.created_at).isoformat(),
        'pembeli': p.customer or '',
        'metode': p.metode,
        'metode_label': METODE_LABEL.get(p.metode, ''),
        'total': int(p.total),
        'jumlah_item': p.items,
        'is_void': bool(p.is_void),
        'jatuh_tempo': p.jatuh_tempo.isoformat() if p.jatuh_tempo else None,
        'reprint': p.reprint_nota,
    }
    if with_items:
        data['items'] = [
            {'barang_id': d.barang_id, 'nama': d.barang.nama, 'jumlah': d.jumlah,
             'harga': int(d.harga or 0), 'total': int(d.total or 0)}
            for d in PenjualanDetail.objects.filter(penjualan=p).select_related('barang').order_by('id')
        ]
    return data

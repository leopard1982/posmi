import uuid
import datetime

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase

from pos.models import Penjualan
from stock.models import Barang, Cabang, DaftarPaket, UserProfile

BASE = '/api/mobile/v1/'


class MobileApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.paket = DaftarPaket.objects.create(nama='Bisnis Kecil')
        self.cabang = Cabang.objects.create(nama_toko='Toko A', prefix='aaaa', paket=self.paket,
                                            lisensi_expired=datetime.datetime(2099, 1, 1),
                                            lisensi_grace=datetime.datetime(2099, 1, 1))
        self.other = Cabang.objects.create(nama_toko='Toko B', prefix='bbbb')
        self.user = self._user('aaaa1', self.cabang, superuser=True)
        self.kasir = self._user('aaaa2', self.cabang)
        self.user_b = self._user('bbbb1', self.other)
        self.b1 = Barang.objects.create(cabang=self.cabang, barcode='111', nama='Mie', stok=10,
                                        harga_ecer=3000, harga_grosir=2800, min_beli_grosir=5, harga_beli=2000)
        self.b_other = Barang.objects.create(cabang=self.other, barcode='111', nama='Lain', stok=10,
                                             harga_ecer=1000, harga_grosir=1000, min_beli_grosir=5)

    def _user(self, name, cabang, superuser=False):
        u = User.objects.create_user(name, password='rahasia123', is_superuser=superuser)
        UserProfile.objects.create(user=u, cabang=cabang, nama_lengkap=f'Nama {name}')
        return u

    def _login(self, name='aaaa1'):
        r = self.client.post(BASE + 'auth/login/', {'username': name, 'password': 'rahasia123'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['data']['access'])
        return r.data['data']

    def _checkout(self, items, **extra):
        body = {'nota': str(uuid.uuid4()), 'items': items, 'metode': 0, **extra}
        return self.client.post(BASE + 'sales/checkout/', body, format='json'), body

    def test_requires_auth(self):
        self.assertEqual(self.client.get(BASE + 'products/').status_code, 401)

    def test_login_wrong_password(self):
        r = self.client.post(BASE + 'auth/login/', {'username': 'aaaa1', 'password': 'x'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_login_staff_and_inactive_rejected(self):
        User.objects.create_user('adm', password='rahasia123', is_staff=True)
        r = self.client.post(BASE + 'auth/login/', {'username': 'adm', 'password': 'rahasia123'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.kasir.userprofile.is_active = False
        self.kasir.userprofile.save()
        r = self.client.post(BASE + 'auth/login/', {'username': 'aaaa2', 'password': 'rahasia123'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_products_scoped_and_hide_modal(self):
        self._login()
        r = self.client.get(BASE + 'products/')
        names = [p['nama'] for p in r.data['data']['results']]
        self.assertEqual(names, ['Mie'])
        self.assertNotIn('harga_beli', r.data['data']['results'][0])
        r = self.client.get(BASE + 'products/barcode/111/')
        self.assertEqual(r.data['data']['nama'], 'Mie')

    def test_checkout_ecer_grosir_and_stock(self):
        self._login()
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 2}])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data['data']['total'], 6000)
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 5}])
        self.assertEqual(r.data['data']['total'], 14000)
        self.b1.refresh_from_db()
        self.assertEqual(self.b1.stok, 3)
        self.cabang.refresh_from_db()
        self.assertEqual(self.cabang.no_nota, 3)
        self.assertEqual(self.cabang.kuota_transaksi, 73)

    def test_checkout_idempotent(self):
        self._login()
        r, body = self._checkout([{'barang_id': self.b1.id, 'jumlah': 1}])
        r2 = self.client.post(BASE + 'sales/checkout/', body, format='json')
        self.assertEqual(r2.status_code, 200)
        self.b1.refresh_from_db()
        self.assertEqual(self.b1.stok, 9)

    def test_checkout_insufficient_stock(self):
        self._login()
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 11}])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Penjualan.objects.count(), 0)

    def test_checkout_other_cabang_item(self):
        self._login()
        r, _ = self._checkout([{'barang_id': self.b_other.id, 'jumlah': 1}])
        self.assertEqual(r.status_code, 400)

    def test_custom_price_admin_only(self):
        self._login('aaaa2')
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 1, 'harga': 1}])
        self.assertEqual(r.status_code, 403)
        self._login('aaaa1')
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 2, 'harga': 2500}])
        self.assertEqual(r.data['data']['total'], 5000)

    def test_tempo_requires_due_date_and_paket(self):
        self._login()
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 1}], metode=2)
        self.assertEqual(r.status_code, 400)
        r, _ = self._checkout([{'barang_id': self.b1.id, 'jumlah': 1}], metode=2,
                              jatuh_tempo=str(datetime.date.today() + datetime.timedelta(days=7)))
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(Penjualan.objects.get(nota=r.data['data']['nota']).tgl_bayar)

    def test_history_only_own(self):
        self._login('aaaa2')
        self._checkout([{'barang_id': self.b1.id, 'jumlah': 1}])
        self._login('aaaa1')
        self.assertEqual(self.client.get(BASE + 'sales/').data['data']['count'], 0)
        self._login('aaaa2')
        d = self.client.get(BASE + 'sales/').data['data']
        self.assertEqual(d['count'], 1)
        r = self.client.post(BASE + f"sales/{d['results'][0]['nota']}/reprint/")
        self.assertEqual(r.data['data']['reprint'], 1)

    def test_logout_blacklists_refresh(self):
        tok = self._login()
        self.client.post(BASE + 'auth/logout/', {'refresh': tok['refresh']}, format='json')
        self.client.credentials()
        r = self.client.post(BASE + 'auth/refresh/', {'refresh': tok['refresh']}, format='json')
        self.assertEqual(r.status_code, 401)

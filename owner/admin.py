from django.contrib import admin
from .models import Owner

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ['nama', 'user', 'jumlah_slot', 'kuota_transaksi_pool', 'lisensi_expired', 'is_active']
    search_fields = ['nama', 'user__email']
    readonly_fields = ['id', 'created_at']

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Aktif'

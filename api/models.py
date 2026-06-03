from django.db import models
from stock.models import Cabang
import secrets


class ApiKey(models.Model):
    cabang    = models.OneToOneField(Cabang, on_delete=models.CASCADE, related_name='api_key')
    key       = models.CharField(max_length=64, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used  = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ApiKey: {self.cabang.nama_toko}"


class WebhookEndpoint(models.Model):
    EVENT_CHOICES = [
        ('transaction.completed', 'Transaksi Selesai'),
        ('transaction.voided',    'Transaksi Void'),
        ('stock.low',             'Stok Rendah (< 5)'),
    ]
    cabang     = models.ForeignKey(Cabang, on_delete=models.CASCADE, related_name='webhooks')
    url        = models.URLField(max_length=500)
    event      = models.CharField(max_length=30, choices=EVENT_CHOICES)
    secret     = models.CharField(max_length=64, editable=False)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cabang.nama_toko} → {self.event}"


class WebhookLog(models.Model):
    STATUS_OK   = 'ok'
    STATUS_FAIL = 'fail'
    webhook       = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='logs')
    event         = models.CharField(max_length=30)
    payload       = models.JSONField()
    status        = models.CharField(max_length=10, default=STATUS_FAIL)
    response_code = models.IntegerField(null=True, blank=True)
    error         = models.TextField(blank=True)
    sent_at       = models.DateTimeField(auto_now_add=True)

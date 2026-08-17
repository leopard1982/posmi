from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from cara.models import Tutorial


class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return ['index_pos', 'index_cara', 'tos', 'privacy', 'sla']

    def location(self, item):
        return reverse(item)


class TutorialSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return Tutorial.objects.all().order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse('detail_cara', args=[obj.id])

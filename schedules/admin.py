from django.contrib import admin
from .models import Schedule, Setting, ApiUsage

admin.site.register(Schedule)
admin.site.register(Setting)
admin.site.register(ApiUsage)
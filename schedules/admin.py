from django.contrib import admin

from .models import ApiUsage, Schedule, Setting

admin.site.register(Schedule)
admin.site.register(Setting)
admin.site.register(ApiUsage)
from django.conf import settings

from schedules.models import ApiUsage


def get_today_usage(user, today):
    usage, _ = ApiUsage.objects.get_or_create(
        user=user,
        defaults={'last_used_on': today},
    )
    if usage.last_used_on != today:
        usage.count = 0
        usage.last_used_on = today
        usage.save()
    return usage

def add_usage(usage):
    usage.count += 1
    usage.save()

def get_remaining(usage):
    return max(settings.AI_DAILY_LIMIT - usage.count, 0)
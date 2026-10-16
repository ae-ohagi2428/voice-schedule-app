from datetime import timedelta


def get_schedule_status(schedules, now):
    current_schedule = schedules.filter(start_at__lte=now, end_at__gt=now).first()
    next_schedule = schedules.filter(start_at__gt=now).first()

    state = 'none'
    if current_schedule:
        state = 'running'
    elif next_schedule and next_schedule.start_at - now <= timedelta(minutes=15):
        state = 'soon'
    elif next_schedule:
        state = 'waiting'
    elif schedules.exists():
        state = 'finished'

    return state, current_schedule, next_schedule
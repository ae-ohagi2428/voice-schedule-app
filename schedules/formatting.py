from datetime import datetime, timedelta


def format_schedules(schedules, now):
    # ScheduleItemインスタンスをdict型へ変換
    items = [schedule.model_dump() for schedule in schedules]

    # 日付（文字列型）を日時型へ変換
    for item in items:
        item['start'] = to_datetime(item['start'], now)
        item['end'] = to_datetime(item['end'], now)

    # forループ内でround_up_to_5min()・correct_start()・correct_end()が実行される
    fill_starts(items, now)

    # 開始時刻順に並べ直す作業を定義
    items.sort(key=lambda item: item['start'])

    # forループ内で終了時刻を埋める→開始時刻と同一時刻の場合は+1分
    fill_ends(items)

    return items

# 日付を日時にする処理
def to_datetime(time_str, now):
    if time_str is None:
        return None
    time_conved = datetime.strptime(time_str, '%H:%M')
    time_replaced = now.replace(
        hour=time_conved.hour,
        minute=time_conved.minute,
        second=0,
        microsecond=0,
    )
    return time_replaced

# 日時を5分単位で切り上げるための関数
def round_up_to_5min(dt):
    delta = -dt.minute % 5
    rounded_dt = dt.replace(second=0, microsecond=0) + timedelta(minutes=delta)
    return rounded_dt

# 開始時刻の午前・午後を補正するための関数
def correct_start(start, now):
    if start is None:
        return None
    if start >= now - timedelta(hours=1):
        return start
    if start.hour < 12:
        return start + timedelta(hours=12)
    return start

# 終了時刻を補正するための関数
def correct_end(start, end):
    if end is None:
        return None
    if end < start:
        if end + timedelta(hours=12) <= start:
            return end + timedelta(days=1)
        return end + timedelta(hours=12)
    return end


# for文を定義：1件ずつ：開始時刻の午前・午後の補正→開始時刻を埋める → その予定の終了時刻の午前・午後の補正
def fill_starts(items, now):
    prev_end = None
    for item in items:
        # 開始時刻の補正②午前・午後の補正
        item['start'] = correct_start(item['start'], now)
        
        # 開始時刻を埋める
        if item['start'] is None:
            if item['end'] is not None and item['duration_minutes'] is not None:
                item['start'] = item['end'] - timedelta(minutes=item['duration_minutes'])
            elif prev_end is None:
                item['start'] = round_up_to_5min(now)
            else:
                item['start'] = prev_end

        # 終了時刻の補正
        item['end'] = correct_end(item['start'], item['end'])

        # 次の予定のためにprev_endを入れる
        if item['end'] is not None:
            prev_end = item['end']
        elif item['duration_minutes'] is not None:
            item['end'] = item['start'] + timedelta(minutes=item['duration_minutes'])
            prev_end = item['end']
        else:
            prev_end = item['start'] + timedelta(minutes=60)
    return items

# 終了時刻に関するfor文を定義
def fill_ends(items):
    for i, item in enumerate(items):
        if item['end'] is None:
            if i + 1 < len(items):
                item['end'] = items[i + 1]['start']
            else:
                item['end'] = item['start'] + timedelta(minutes=60)
        if item['end'] == item['start']:
            item['end'] = item['start'] + timedelta(minutes=1)
    return items
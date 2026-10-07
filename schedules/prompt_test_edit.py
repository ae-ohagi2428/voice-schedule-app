from django.utils import timezone

from schedules.ai import ask_ai
from schedules.formatting import to_datetime

today = timezone.localtime()

def iso(hour, minute=0):
    # 今日の日付の時刻を、セッションと同じ文字の形にする
    return today.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()

# 5件とも同じ「今の予定」から始める
base_schedules = [
    {'title': '散歩', 'start_at': iso(10), 'end_at': iso(11)},
    {'title': '昼ごはん', 'start_at': iso(12), 'end_at': iso(13)},
    {'title': '勉強', 'start_at': iso(14), 'end_at': iso(16)},
]

sample_text = [
    '散歩を10時半からにして',
    '昼ごはんは1時半まで',
    '勉強はやめる',
    '5時から買い物も入れて1時間',
    '散歩じゃなくてジョギング',
]

now_time = ['09:00'] * 5

current_schedules = [base_schedules] * 5

correct_output = [
    {
        'schedules': [
            {'title': '散歩', 'start': '10:30', 'end': '11:30', 'duration_minutes': None},
            {'title': '昼ごはん', 'start': '12:00', 'end': '13:00', 'duration_minutes': None},
            {'title': '勉強', 'start': '14:00', 'end': '16:00', 'duration_minutes': None},
        ]
    },
    {
        'schedules': [
            {'title': '散歩', 'start': '10:00', 'end': '11:00', 'duration_minutes': None},
            {'title': '昼ごはん', 'start': '12:00', 'end': '13:30', 'duration_minutes': None},
            {'title': '勉強', 'start': '14:00', 'end': '16:00', 'duration_minutes': None},
        ]
    },
    {
        'schedules': [
            {'title': '散歩', 'start': '10:00', 'end': '11:00', 'duration_minutes': None},
            {'title': '昼ごはん', 'start': '12:00', 'end': '13:00', 'duration_minutes': None},
        ]
    },
    {
        'schedules': [
            {'title': '散歩', 'start': '10:00', 'end': '11:00', 'duration_minutes': None},
            {'title': '昼ごはん', 'start': '12:00', 'end': '13:00', 'duration_minutes': None},
            {'title': '勉強', 'start': '14:00', 'end': '16:00', 'duration_minutes': None},
            {'title': '買い物', 'start': '17:00', 'end': '18:00', 'duration_minutes': 60},
        ]
    },
    {
        'schedules': [
            {'title': 'ジョギング', 'start': '10:00', 'end': '11:00', 'duration_minutes': None},
            {'title': '昼ごはん', 'start': '12:00', 'end': '13:00', 'duration_minutes': None},
            {'title': '勉強', 'start': '14:00', 'end': '16:00', 'duration_minutes': None},
        ]
    },
]

def first_test(sample_text, now_time, current_schedules):
    answer_list = []
    today = timezone.localtime()
    for text, now, schedules in zip(sample_text, now_time, current_schedules, strict=True):
        ai_answer = ask_ai(text, to_datetime(now, today), current_schedules=schedules)
        answer_list.append(ai_answer.model_dump())
    return answer_list

def check_results(answer_list, correct_output):
    match_count = 0
    for i, (answer, correct) in enumerate(zip(answer_list, correct_output, strict=True), start=1):
        is_match = answer['schedules'] == correct['schedules']
        if is_match:
            match_count += 1
        print(f'--- {i}個目：{"一致" if is_match else "不一致"} ---')
        print('タスク名：', [item['title'] for item in answer['schedules']])
        if not is_match:
            print('AIの答え：', answer['schedules'])
            print('正解　　：', correct['schedules'])
    print(f'{len(correct_output)}件中 {match_count}件一致')

answer_list = first_test(sample_text, now_time, current_schedules)
check_results(answer_list, correct_output)
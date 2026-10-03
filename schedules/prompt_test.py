from django.utils import timezone

from schedules.ai import ask_ai
from schedules.formatting import to_datetime

sample_text = [
    "午後3時にカフェに行き午後4時まで滞在するそのあと買い物に行く60分かかる",
    "10時に勉強を始める180分やる2時に友達の家に行く4時まで過ごす5時からご飯を作る",
    "まず朝の運動をする1時間半かかる正午に昼ごはんを食べる1時間くらいかな",
    "3時半に散歩に出かける1時間半かかる",
    "9時から10時まで病院に行く11時からカフェで作業明日は15時にモンブランを食べたいな",
    "9時いや10時から見たいテレビがある30分それから風呂に入る11時になる",
    "7時から1時間くらい朝ごはんそのあと買い物そのあと掃除そのあと1時間休憩",
    "正午に昼ごはんを食べる15時から歯医者16時までの予定",
    "午前10時にパイソン60分午前11時にエスキューエル60分午後3時から午後5時まで掃除",
    "これから8時まで勉強する10時になったら洗濯を回す9時から1時間病院の予約があるんだった忘れてたあとなんだっけ？夜8時に見たいテレビあるんだった60分番組のやつ楽しみ",
]

now_time = [
    "14:00",
    "09:03",
    "06:00",
    "09:15",
    "06:09",
    "15:05",
    "07:00",
    "09:00",
    "10:00",
    "07:07",
]

correct_output = [
    {
      "schedules": [
        {"title": "カフェ", "start": "15:00", "end": "16:00", "duration_minutes": None},
        {"title": "買い物", "start": None, "end": None, "duration_minutes": 60}
      ]
    },
    {
      "schedules": [
        {"title": "勉強", "start": "10:00", "end": None, "duration_minutes": 180},
        {"title": "友達の家に行く", "start": "14:00", "end": "16:00", "duration_minutes": None},
        {"title": "ご飯を作る", "start": "17:00", "end": None, "duration_minutes": None}
      ]
    },
    {
      "schedules": [
        {"title": "朝の運動", "start": None, "end": None,
        "duration_minutes": 90},
        {"title": "昼ごはん", "start": "12:00", "end": None,
        "duration_minutes": 60}
      ]
    },
    {
      "schedules": [
        {"title": "散歩", "start": "15:30", "end": None,
        "duration_minutes": 90}
      ]
    },
    {
      "schedules": [
        {"title": "病院に行く", "start": "09:00", "end": "10:00",
        "duration_minutes": None},
        {"title": "カフェで作業", "start": "11:00", "end": None,
        "duration_minutes": None}
      ]
    },
    {
      "schedules": [
        {"title": "テレビを見る", "start": "22:00", "end": None,
        "duration_minutes": 30},
        {"title": "風呂に入る", "start": None, "end": "23:00",
        "duration_minutes": None}
      ]
    },
    {
      "schedules": [
        {"title": "朝ごはん", "start": "07:00", "end": None,
        "duration_minutes": 60},
        {"title": "買い物", "start": None, "end": None,
        "duration_minutes": None},
        {"title": "掃除", "start": None, "end": None,
        "duration_minutes": None},
        {"title": "休憩", "start": None, "end": None,
        "duration_minutes": 60}
      ]
    },
    {
      "schedules": [
        {"title": "昼ごはん", "start": "12:00", "end": None,
        "duration_minutes": None},
        {"title": "歯医者", "start": "15:00", "end": "16:00",
        "duration_minutes": None}
      ]
    },
    {
    "schedules": [
        {"title": "パイソン", "start": "10:00", "end": None,
        "duration_minutes": 60},
        {"title": "エスキューエル", "start": "11:00", "end": None,
        "duration_minutes": 60},
        {"title": "掃除", "start": "15:00", "end": "17:00",
        "duration_minutes": None}
      ]
    },
    {
    "schedules": [
        {"title": "勉強", "start": None, "end": "08:00",
        "duration_minutes": None},
        {"title": "洗濯を回す", "start": "10:00", "end": None,
        "duration_minutes": None},
        {"title": "病院の予約", "start": "09:00", "end": None,
        "duration_minutes": 60},
        {"title": "テレビ", "start": "20:00", "end": None,
        "duration_minutes": 60}
      ]
    },
]

def first_test(sample_text, now_time):
    answer_list = []
    today = timezone.localtime()
    for text, now in zip(sample_text, now_time, strict=True):
        ai_answer = ask_ai(text, to_datetime(now, today))
        answer_list.append(ai_answer.model_dump())
    return answer_list

def remove_title(schedules):
    return [{k: v for k, v in item.items() if k != 'title'} for item in schedules]


def check_results(answer_list, correct_output):
    match_count = 0
    for i, (answer, correct) in enumerate(zip(answer_list, correct_output, strict=True), start=1):
        is_match = remove_title(answer['schedules']) == remove_title(correct['schedules'])
        if is_match:
            match_count += 1
        print(f'--- {i}個目：{"一致" if is_match else "不一致"} ---')
        print('タスク名：', [item['title'] for item in answer['schedules']])
        if not is_match:
            print('AIの答え：', remove_title(answer['schedules']))
            print('正解　　：', remove_title(correct['schedules']))
    print(f'{len(correct_output)}件中 {match_count}件一致')

answer_list = first_test(sample_text, now_time)
check_results(answer_list, correct_output)
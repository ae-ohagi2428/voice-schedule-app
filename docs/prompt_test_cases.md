### ルール
- AIが返すべき値はPythonで埋める前の値である
- タスク名は意味が合っていればOK
### 1
#### 今の時刻
14:00
#### 音声入力
午後3時にカフェに行き午後4時まで滞在するそのあと買い物に行く60分かかる
#### AIが返すべき値
{
  "schedules": [
    {"title": "カフェ", "start": "15:00", "end": "16:00", "duration_minutes": null},
    {"title": "買い物", "start": null, "end": null, "duration_minutes": 60}
  ]
}
### 2
#### 今の時刻
09:03
#### 音声入力
10時に勉強を始める180分やる2時に友達の家に行く4時まで過ごす5時からご飯を作る
#### AIが返すべき値
{
  "schedules": [
    {"title": "勉強", "start": "10:00", "end": null, "duration_minutes": 180},
    {"title": "友達の家に行く", "start": "14:00", "end": "16:00", "duration_minutes": null},
    {"title": "ご飯を作る", "start": "17:00", "end": null, "duration_minutes": null}
  ]
}
### 3
#### 今の時刻
06:00
#### 音声入力
まず朝の運動をする1時間半かかる正午に昼ごはんを食べる1時間くらいかな
#### AIが返すべき値
{
  "schedules": [
    {"title": "朝の運動", "start": null, "end": null,
    "duration_minutes": 90},
    {"title": "昼ごはん", "start": "12:00", "end": null,
    "duration_minutes": 60}
  ]
}
### 4
#### 今の時刻
09:15
#### 音声入力
3時半に散歩に出かける1時間半かかる
#### AIが返すべき値
{
  "schedules": [
    {"title": "散歩", "start": "15:30", "end": null,
    "duration_minutes": 90}
  ]
}
### 5
#### 今の時刻
06:09
#### 音声入力
9時から10時まで病院に行く11時からカフェで作業明日は15時にモンブランを食べたいな
#### AIが返すべき値
{
  "schedules": [
    {"title": "病院に行く", "start": "09:00", "end": "10:00",
    "duration_minutes": null},
    {"title": "カフェで作業", "start": "11:00", "end": null,
    "duration_minutes": null}
  ]
}
### 6
#### 今の時刻
15:05
#### 音声入力
9時いや10時から見たいテレビがある30分それから風呂に入る11時になる
#### AIが返すべき値
{
  "schedules": [
    {"title": "テレビを見る", "start": "22:00", "end": null,
    "duration_minutes": 30},
    {"title": "風呂に入る", "start": null, "end": "23:00",
    "duration_minutes": null}
  ]
}
### 7
#### 今の時刻
07:00
#### 音声入力
7時から1時間くらい朝ごはんそのあと買い物そのあと掃除そのあと1時間休憩
#### AIが返すべき値
{
  "schedules": [
    {"title": "朝ごはん", "start": "07:00", "end": null,
    "duration_minutes": 60},
    {"title": "買い物", "start": null, "end": null,
    "duration_minutes": null},
    {"title": "掃除", "start": null, "end": null,
    "duration_minutes": null},
    {"title": "休憩", "start": null, "end": null,
    "duration_minutes": 60}
  ]
}
### 8
#### 今の時刻
09:00
#### 音声入力
正午に昼ごはんを食べる15時から歯医者16時までの予定
#### AIが返すべき値
{
  "schedules": [
    {"title": "昼ごはん", "start": "12:00", "end": null,
    "duration_minutes": null},
    {"title": "歯医者", "start": "15:00", "end": "16:00",
    "duration_minutes": null}
  ]
}
### 9
#### 今の時刻
10:00
#### 音声入力
午前10時にパイソン60分午前11時にエスキューエル60分午後3時から午後5時まで掃除
#### AIが返すべき値
{
  "schedules": [
    {"title": "パイソン", "start": "10:00", "end": null,
    "duration_minutes": 60},
    {"title": "エスキューエル", "start": "11:00", "end": null,
    "duration_minutes": 60},
    {"title": "掃除", "start": "15:00", "end": "17:00",
    "duration_minutes": null}
  ]
}
### 10
#### 今の時刻
07:07
#### 音声入力
これから8時まで勉強する10時になったら洗濯を回す9時から1時間病院の予約があるんだった忘れてたあとなんだっけ？夜8時に見たいテレビあるんだった60分番組のやつ楽しみ
#### AIが返すべき値
{
  "schedules": [
    {"title": "勉強", "start": null, "end": "08:00",
    "duration_minutes": null},
    {"title": "洗濯を回す", "start": "10:00", "end": null,
    "duration_minutes": null},
    {"title": "病院の予約", "start": "09:00", "end": null,
    "duration_minutes": 60},
    {"title": "テレビ", "start": "20:00", "end": null,
    "duration_minutes": 60}
  ]
}
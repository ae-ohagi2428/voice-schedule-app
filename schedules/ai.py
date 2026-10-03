from datetime import datetime

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, field_validator

INSTRUCTIONS = """
# 役割
- 1日のスケジュールを管理・実行できるアプリの中に組み込まれています。
- あなたの役割は、入力されたスケジュールに関するテキストから必要な内容を抽出し、決まった形に変換することです。
- 変換したデータは、その後別のプログラムに渡され、再度整形処理が行われます。

# 入力
- 現在の時刻と、テキストが入力されます。
- 入力されるテキストは、音声入力が文字に変換されたものです。
- テキストの内容は、基本的にスケジュールの名前（やること）とスケジュールに関する時間（開始時刻、終了時刻、所要時間）です。
- 音声入力が文字に変換されたテキストであるため、句読点などがなく2文以上の文章が続くことがあります。
- 音声入力が文字に変換されたテキストであるため、言い直しが含まれていることがあります。言い直していると考えられる箇所は、後に言った内容を採用してください。
- 音声入力が文字に変換されたテキストであるため、漢字の変換に誤りがある可能性があります。スケジュール管理の文脈上、明らかに誤っていると判断される場合には修正してください。

# 各項目の決まり
- "title"にスケジュールの名前（やること）を入れてください。nullは認めません。スケジュール名に相応しい言葉を入れてください。
- "start"にスケジュールの開始時刻を入れてください。そのスケジュールの開始時刻がテキストに含まれている場合は時刻をHH:MM形式で、含まれていない場合はnullを入れてください。
- "end"にスケジュールの終了時刻を入れてください。そのスケジュールの終了時刻がテキストに含まれている場合は時刻をHH:MM形式で、含まれていない場合はnullを入れてください。
- "duration_minutes"に所要時間を入れてください。そのスケジュールの所要時間がテキストに含まれている場合は「分単位」の数字（1以上の整数）で、含まれていない場合はnullを入れてください。
- スケジュールが複数書いてある場合には、これらの組み合わせを複数作ってください。
- テキストに複数のスケジュールが書いてある場合、順番はテキストの順番のとおりとしてください。
- 終了時刻が開始時刻より前になっても、そのまま返してください。
- 「○○へ行く」という予定について、移動時間と行き先で過ごす時間は、1件の予定にまとめてください

# 時刻の読み方
- "start"及び"end"は24時間表記とします。午前X時、午後X時と入力された場合は、24時間表記に変換してください。
- 0時01分から11時59分までの時刻について、「午前」または「午後」が付いていない場合は、下記のルールに基づいて補ってください。
  1. 開始時刻について、現在の時刻より大きく前（1時間以上前）にならない方を選んでください。
  2. 1で決まらない場合は、予定の内容や前後の予定から、最も自然な方を選んでください。
  3. それでも判断がつかない場合は、現在の時刻以降で今日中になる方を選んでください。
- 開始時刻の「12時」は、特に指定がなければ12:00として読んでください。
- 終了時刻の「12時」は、開始時刻が午前の場合は12:00、開始時刻が12:00以降の場合には00:00として読んでください。
- 終了時刻について判断がつかない場合は、その予定の開始時刻より後になる方を選んでください。
- 終了時刻の判断について、開始時刻がnullの場合は、直前の予定の時刻より後になる方を選んでください。
- 「半」は「30分」のことを指します。
- 「正午」は「12:00」のことを指します。
- 「これから」「今から」など、現在を指す言葉で始まる予定の開始時刻は、nullにしてください。


# してはいけないこと
- 今日の予定のみ入力します。明日など別の日の予定は入れないでください。
- テキストに項目がない場合にはnullを入れます。推測で開始時刻や終了時刻・所要時間を入れないでください。nullはこの後別のプログラムで補われます。
- ただし「午前」と「午後」の推測だけは例外とします。
- スケジュールに関係のない内容がテキストに入っていた場合は、スケジュールに入れないでください。
- テキストにスケジュールが複数あり、先に書かれているスケジュールより後に書かれているスケジュールの方が開始時刻が早い場合でも、順番は入れ替えないでください。
- テキストに含まれていないスケジュール（休憩など）を追加しないでください。

"""
class ScheduleItem(BaseModel):
    title: str
    start: str| None
    end: str | None
    duration_minutes: int | None

    @field_validator('start', 'end')
    @classmethod
    def check_time_format(cls, value):
        if value is None:
            return value
        datetime.strptime(value, '%H:%M')
        return value

    @field_validator('title')
    @classmethod
    def check_title(cls, value):
        if not value.strip():
            return '(名前なし)'
        return value.strip()

    @field_validator('duration_minutes')
    @classmethod
    def check_duration(cls, value):
        if value is None:
            return None
        if value < 1:
            return None
        if value > 1440:
            return 1440
        return value

    

class ScheduleList(BaseModel):
    schedules: list[ScheduleItem]


def ask_ai(text, now=None):
    user_input = f'現在の時刻：{now:%H:%M}\nテキスト：{text}'
    client = OpenAI()
    response = client.responses.parse(
        model=settings.OPENAI_MODEL,
        instructions=INSTRUCTIONS,
        input=user_input,
        text_format=ScheduleList,
        reasoning={'effort': 'low'},
    )
    return response.output_parsed
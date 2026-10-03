from datetime import datetime, timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from pydantic import ValidationError

from schedules.formatting import (
    correct_end,
    correct_start,
    format_schedules,
    round_up_to_5min,
    to_datetime,
)

from .ai import ScheduleItem
from .factories import ScheduleFactory

NOW = timezone.make_aware(datetime(2026, 10, 1, 15, 5))

class ScheduleFactoryTest(TestCase):
    def test_create_schedule(self):
        schedule = ScheduleFactory()
        self.assertLess(schedule.start_at, schedule.end_at)
        self.assertIsNotNone(schedule.user)

class ScheduleItemValidationTest(SimpleTestCase):
    def test_valid_time_passes(self):
        item = ScheduleItem(title='カフェ', start='15:00', end=None, duration_minutes=None)
        self.assertEqual(item.start, '15:00')

    def test_invalid_start_time_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='カフェ', start='25:00', end=None, duration_minutes=None)

    def test_invalid_end_time_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='ヨガ', start=None, end='25:00', duration_minutes=None)

    def test_start_invalid_format_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='勉強', start='15時', end=None, duration_minutes=None)

    def test_end_invalid_format_raises_error(self):
        with self.assertRaises(ValidationError):
            ScheduleItem(title='外出', start=None, end='18時', duration_minutes=None)

    def test_valid_title_passes(self):
        item = ScheduleItem(title='予定あり', start=None, end=None, duration_minutes=None)
        self.assertEqual(item.title, '予定あり')

    def test_empty_title_is_complemented(self):
        item = ScheduleItem(title='', start=None, end=None, duration_minutes=None)
        self.assertEqual(item.title, '(名前なし)')

    def test_valid_duration_minutes_passes(self):
        item = ScheduleItem(title='皿洗い', start=None, end=None, duration_minutes=15)
        self.assertEqual(item.duration_minutes, 15)

    def test_none_duration_minutes_passes(self):
        item = ScheduleItem(title='図書館', start=None, end=None, duration_minutes=None)
        self.assertIsNone(item.duration_minutes)

    def test_zero_duration_minutes_becomes_none(self):
        item = ScheduleItem(title='買い物', start=None, end=None, duration_minutes=0)
        self.assertIsNone(item.duration_minutes)

    def test_minus_duration_minutes_becomes_none(self):
        item = ScheduleItem(title='Pythonの勉強', start=None, end=None, duration_minutes=-10)
        self.assertIsNone(item.duration_minutes)

    def test_dm_over_1440_becomes_1440(self):
        item = ScheduleItem(title='旅行', start=None, end=None, duration_minutes=1441)
        self.assertEqual(item.duration_minutes, 1440)

    def test_dm_equal_1440_passes(self):
        item = ScheduleItem(title='出張', start=None, end=None, duration_minutes=1440)
        self.assertEqual(item.duration_minutes, 1440)


class FormattingFunctionTest(SimpleTestCase):
    # to_datetime
    def test_to_datetime_converts_time_string(self):
        dt = NOW.replace(hour=15, minute=0, second=0, microsecond=0)
        self.assertEqual(to_datetime('15:00', NOW), dt)

    def test_to_datetime_returns_none_for_none(self):
        self.assertIsNone(to_datetime(None, NOW))

    # round_up_to_5min
    def test_round_up_to_5min_rounds_up(self):
        dt = NOW.replace(hour=14, minute=7)
        self.assertEqual(
            round_up_to_5min(dt),
            NOW.replace(hour=14, minute=10, second=0, microsecond=0)
        )

    def test_round_up_to_5min_keeps_exact_5min(self):
        dt = NOW.replace(hour=14, minute=10)
        self.assertEqual(round_up_to_5min(dt), dt)

    def test_round_up_to_5min_carries_over_to_next_hour(self):
        dt = NOW.replace(hour=14, minute=58)
        self.assertEqual(
            round_up_to_5min(dt),
            NOW.replace(hour=15, minute=0,  second=0, microsecond=0)
        )

    # correct_start
    def test_correct_start_keeps_time_within_1_hour_before(self):
        dt = NOW.replace(hour=14, minute=30)
        self.assertEqual(correct_start(dt, NOW), dt)

    def test_correct_start_adds_12_hours_to_morning_time(self):
        dt = NOW.replace(hour=10, minute=0)
        self.assertEqual(
            correct_start(dt, NOW),
            NOW.replace(hour=22, minute=0, second=0, microsecond=0)  
        )

    def test_correct_start_returns_none_for_none(self):
        self.assertIsNone(correct_start(None, NOW))

    # correct_end
    def test_correct_end_adds_12_hours(self):
        start = NOW.replace(hour=22, minute=30)
        end = NOW.replace(hour=11, minute=0)
        self.assertEqual(correct_end(start, end), NOW.replace(hour=23, minute=0))
    
    def test_correct_end_adds_1_day_when_crossing_midnight(self):
        start = NOW.replace(hour=23, minute=0)
        end = NOW.replace(hour=1, minute=0)
        self.assertEqual(
            correct_end(start, end),
            NOW.replace(hour=1, minute=0) + timedelta(days=1)
        )

    def test_correct_end_keeps_same_time_as_start(self):
        start = NOW.replace(hour=12, minute=0)
        end = NOW.replace(hour=12, minute=0)
        self.assertEqual(correct_end(start, end), end)

class FormatSchedulesTest(SimpleTestCase):
    def test_case6_corrected(self):
        schedules = [
            ScheduleItem(title='テレビを見る', start='10:00', end=None, duration_minutes=30),
            ScheduleItem(title='風呂に入る', start=None, end='11:00', duration_minutes=None),
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[0]['start'], NOW.replace(hour=22, minute=0, second=0, microsecond=0))
        self.assertEqual(result[0]['end'], NOW.replace(hour=22, minute=30, second=0, microsecond=0))
        self.assertEqual(result[1]['start'], NOW.replace(hour=22, minute=30, second=0, microsecond=0))
        self.assertEqual(result[1]['end'], NOW.replace(hour=23, minute=0, second=0, microsecond=0))

    def test_first_start_none_uses_rounded_now(self):
        now = NOW.replace(minute=7)
        schedules = [
            ScheduleItem(title='買い物', start=None, end='16:00', duration_minutes=None),
            ScheduleItem(title='掃除', start='17:00', end='18:00', duration_minutes=None)
        ]
        result = format_schedules(schedules, now)
        self.assertEqual(result[0]['start'], NOW.replace(minute=10, second=0, microsecond=0))
        
    def test_sorted_by_start_time(self):
        now = NOW.replace(hour=6, minute=30)
        schedules = [
            ScheduleItem(title='勉強', start='07:00', end='08:00', duration_minutes=None),
            ScheduleItem(title='洗濯を回す', start='10:00', end=None, duration_minutes=60),
            ScheduleItem(title='病院の予約', start='09:00', end=None, duration_minutes=60)
        ]
        result = format_schedules(schedules, now)
        self.assertEqual(result[0]['title'], '勉強')
        self.assertEqual(result[1]['title'], '病院の予約')
        self.assertEqual(result[2]['title'], '洗濯を回す')

    def test_last_end_none_becomes_start_plus_1_hour(self):
        schedules = [
            ScheduleItem(title='夜ご飯を作る', start='18:00', end='19:00', duration_minutes=None),
            ScheduleItem(title='夜ご飯', start='19:00', end=None, duration_minutes=None)
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[1]['end'], NOW.replace(hour=20, minute=0))

    def test_same_start_and_end_adds_1_minute(self):
        schedules = [
            ScheduleItem(title='炊飯予約', start='17:00', end='17:00', duration_minutes=None),
        ]
        result = format_schedules(schedules, NOW)
        self.assertEqual(result[0]['end'], NOW.replace(hour=17, minute=1))
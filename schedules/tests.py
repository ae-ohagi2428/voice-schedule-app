from django.test import SimpleTestCase, TestCase
from pydantic import ValidationError

from .ai import ScheduleItem
from .factories import ScheduleFactory


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
            
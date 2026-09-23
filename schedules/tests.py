from django.test import TestCase

from .factories import ScheduleFactory


class ScheduleFactoryTest(TestCase):
    def test_create_schedule(self):
        schedule = ScheduleFactory()
        self.assertLess(schedule.start_at, schedule.end_at)
        self.assertIsNotNone(schedule.user)

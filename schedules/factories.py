from datetime import timedelta

import factory
from django.utils import timezone
from accounts.factories import UserFactory
from .models import Schedule

class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Schedule

    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'予定{n}')
    start_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    end_at = factory.LazyAttribute(lambda o: o.start_at + timedelta(minutes=30))
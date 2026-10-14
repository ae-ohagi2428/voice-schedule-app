from datetime import datetime, timedelta
from itertools import combinations

from django import forms
from django.utils import timezone

from .models import Schedule


# 予定1件分のフォームをつくる
class ScheduleEditForm(forms.ModelForm):
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        error_messages={'required': '開始時刻を入れてね'}
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        error_messages={'required': '終了時刻を入れてね'}
    )

    class Meta:
        model = Schedule
        fields = ['title']
        error_messages = {
             'title': {'required': 'タスク名を入れてね'},
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # 既存の予定なら、start_at, end_atから時刻を取り出して、入力欄の初期値にする
        if self.instance.pk:
            self.initial['start_time'] = timezone.localtime(self.instance.start_at).time()
            self.initial['end_time'] = timezone.localtime(self.instance.end_at).time()
        for field in self.fields.values():
                    field.widget.attrs['class'] = 'input'

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time == end_time:
            raise forms.ValidationError('開始時刻と終了時刻は一緒にはできないよ')
        return cleaned_data  

    def get_datetimes(self):
        # start_time・end_time と今日の日付から、start_at・end_at を組み立てる
        start_time = self.cleaned_data['start_time']
        end_time = self.cleaned_data['end_time']
        today = timezone.localdate()
        start_datetime = datetime.combine(today, start_time)
        end_datetime = datetime.combine(today, end_time)
        start_at = timezone.make_aware(start_datetime)
        end_at = timezone.make_aware(end_datetime)
        
        if end_at < start_at:
            end_at = end_at + timedelta(days=1)
        return start_at, end_at

    def save(self, commit=True):
        instance = super().save(commit=False)
        start_at, end_at = self.get_datetimes()
        instance.start_at = start_at
        instance.end_at = end_at

        if not instance.pk:
            instance.user = self.user

        if commit:
            instance.save()
        return instance

    def has_changed(self):
        return True


class BaseScheduleFormSet(forms.BaseModelFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        items = []
        for form in self.forms:
            if not form.cleaned_data.get('DELETE'):
                start_at, end_at = form.get_datetimes()
                items.append({'form': form, 'start': start_at, 'end': end_at})
        for a, b in combinations(items, 2):
            if a['start'] < b['end'] and b['start'] < a['end']:
                a['form'].add_error(
                    None,
                    f"{b['form'].cleaned_data['title']}({b['start']:%H:%M}～{b['end']:%H:%M})と時間が重なってるみたい。重ならない時間に直してね"
                )
                b['form'].add_error(
                    None,
                    f"{a['form'].cleaned_data['title']}({a['start']:%H:%M}～{a['end']:%H:%M})と時間が重なってるみたい。重ならない時間に直してね"
                )
        
        user = self.form_kwargs.get('user')
        today = timezone.localdate()
        ids = {form.instance.pk for form in self.forms if form.instance.pk}
        schedules = Schedule.objects.filter(user=user, start_at__date=today).exclude(pk__in=ids)
        for schedule in schedules:
            db_start = timezone.localtime(schedule.start_at)
            db_end = timezone.localtime(schedule.end_at)
            for item in items:
                if item['start'] < db_end and db_start < item['end']:
                    item['form'].add_error(
                        None,
                        f"{schedule.title}({db_start:%H:%M}〜{db_end:%H:%M})と時間が重なってるみたい。重ならない時間に直してね"
                    )
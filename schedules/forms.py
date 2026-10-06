from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from .models import Schedule


# 予定1件分のフォームをつくる
class ScheduleEditForm(forms.ModelForm):
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
    )

    class Meta:
        model = Schedule
        fields = ['title']

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
        if start_time == end_time:
            raise forms.ValidationError('開始時刻と終了時刻は一緒にはできないよ')
        return cleaned_data  
        
    def save(self, commit=True):
        # start_time・end_time と今日の日付から、start_at・end_at を組み立てて保存する
        instance = super().save(commit=False)
        start_time = self.cleaned_data['start_time']
        end_time = self.cleaned_data['end_time']
        today = timezone.localdate()
        start_datetime = datetime.combine(today, start_time)
        end_datetime = datetime.combine(today, end_time)
        start_at = timezone.make_aware(start_datetime)
        end_at = timezone.make_aware(end_datetime)

        if end_at < start_at:
            end_at = end_at + timedelta(days=1)

        instance.start_at = start_at
        instance.end_at = end_at

        if not instance.pk:
            instance.user = self.user

        if commit:
            instance.save()
        return instance

    def has_changed(self):
        return True
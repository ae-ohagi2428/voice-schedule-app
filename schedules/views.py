import json
from datetime import datetime

import openai
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView
from pydantic import ValidationError

from .ai import ask_ai
from .formatting import format_schedules
from .models import Schedule
from .usage import add_usage, get_remaining, get_today_usage


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context


class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/input.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        usage = get_today_usage(self.request.user, today)
        context['remaining'] = get_remaining(usage)
        return context


class TranscriptView(LoginRequiredMixin, View):
    def post(self, request):
        data = json.loads(request.body)
        text = data.get('text', '')

        if not text.strip():
            return JsonResponse({'error': 'うまく聞き取れなかったよ。もう一度話してね。'}, status=400)
        
        now = timezone.localtime()
        today = now.date()
        usage = get_today_usage(request.user, today)

        if usage.count >= settings.AI_DAILY_LIMIT:
            return JsonResponse({'error': '今日は5回使ったよ。また明日話してね。'}, status=429)
        
        try:
            result = ask_ai(text, now)
        except openai.OpenAIError:
            return JsonResponse({'error': 'AIに接続できなかったよ。少し待ってから試してね。'}, status=503)
        except ValidationError:
            add_usage(usage)
            return JsonResponse({'error': 'うまく読み取れなかったよ。もう一度話してね。'}, status=502)

        add_usage(usage)
        remaining = get_remaining(usage)
        
        if not result.schedules:
            return JsonResponse({'error': '予定が見つからなかったよ。もう一度話してね。', 'remaining': remaining}, status=422)
        formatted = format_schedules(result.schedules, now)
        request.session['new_schedules'] = [
            {
                'title': item['title'],
                'start_at': item['start'].isoformat(),
                'end_at': item['end'].isoformat(),
            }
            for item in formatted
        ]
        return JsonResponse({
            'redirect_url': reverse('schedules:edit'), 'remaining': remaining,
            })


class ScheduleEditView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/edit.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        existing = [
            {'title': s.title, 'start_at': s.start_at, 'end_at': s.end_at, 'is_new': False}
            for s in Schedule.objects.filter(user=self.request.user, start_at__date=today)
        ]
        new = [
            {
                'title': s['title'],
                'start_at': datetime.fromisoformat(s['start_at']),
                'end_at': datetime.fromisoformat(s['end_at']),
                'is_new': True,
            }
            for s in self.request.session.get('new_schedules', [])
        ]
        context['schedules'] = sorted(existing + new, key=lambda s: s['start_at'])
        return context


class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_update.html'


class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'


# TODO: 設定画面の Issue で UpdateView に作り替える
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
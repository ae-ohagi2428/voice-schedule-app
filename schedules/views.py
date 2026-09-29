import json

import openai
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView
from pydantic import ValidationError

from .ai import ask_ai


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context

class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/input.html'

class TranscriptView(LoginRequiredMixin, View):
    def post(self, request):
        data = json.loads(request.body)
        text = data.get('text', '')

        if not text.strip():
            return JsonResponse({'error': 'うまく聞き取れなかったよ。もう一度話してね。'}, status=400)
        try:
            result = ask_ai(text)
        except openai.OpenAIError:
            return JsonResponse({'error': 'AIに接続できなかったよ。少し待ってから試してね。'}, status=503)
        except ValidationError:
            return JsonResponse({'error': 'うまく読み取れなかったよ。もう一度話してね。'}, status=502)

        if not result.schedules:
            return JsonResponse({'error': '予定が見つからなかったよ。もう一度話してね。'}, status=422)

        return JsonResponse(result.model_dump())
    
class ScheduleEditView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_edit.html'

class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_update.html'

class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'

# TODO: 設定画面の Issue で UpdateView に作り替える
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
import json
from datetime import datetime

import openai
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, UpdateView
from pydantic import ValidationError

from .ai import ask_ai
from .formatting import format_schedules
from .forms import ScheduleEditForm
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
        request.session['new_schedules_date'] = today.isoformat()
        return JsonResponse({
            'redirect_url': reverse('schedules:edit'), 'remaining': remaining,
            })


class ScheduleEditView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/edit.html'

    def get_formset(self, data=None):
        today = timezone.localdate()
        existing = Schedule.objects.filter(user=self.request.user, start_at__date=today).order_by('start_at')
        new_schedules = []
        if self.request.session.get('new_schedules_date') == today.isoformat():
            new_schedules = self.request.session.get('new_schedules', [])
        form_list = []
        for schedule in new_schedules:
            start_time = datetime.fromisoformat(schedule['start_at']).time()
            end_time = datetime.fromisoformat(schedule['end_at']).time()
            form_list.append({
                'title': schedule['title'],
                'start_time': start_time,
                'end_time': end_time
            })
        ScheduleFormSet = modelformset_factory(
            Schedule,
            form=ScheduleEditForm,
            extra=len(new_schedules)
        )
        formset = ScheduleFormSet(
            queryset=existing,
            initial=form_list,
            form_kwargs={'user': self.request.user},
            data=data
        )
        return formset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = self.get_formset()
        return context

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(request.POST)
        if formset.is_valid():
            formset.save()
            request.session.pop('new_schedules', None)
            request.session.pop('new_schedules_date', None)
            if request.POST.get('action') == 'add':
                return redirect(f"{reverse('schedules:input')}?mode=add")
            return redirect('schedules:task_run')
        context = self.get_context_data()
        context['formset'] = formset
        return self.render_to_response(context)



class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_update.html'


class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'


# TODO: 設定画面の Issue で UpdateView に作り替える
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
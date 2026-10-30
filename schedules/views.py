import functools
import json
from datetime import datetime

import openai
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import modelformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from google.api_core.exceptions import GoogleAPIError
from google.cloud import texttospeech
from google.oauth2 import service_account
from pydantic import ValidationError

from .ai import ask_ai
from .formatting import format_schedules
from .forms import BaseScheduleFormSet, ScheduleEditForm
from .models import Schedule, Setting
from .status import get_schedule_status
from .usage import add_usage, get_remaining, get_today_usage

SPEECH_MAX_LENGTH = 500
SPEECH_STYLE_PROMPT = 'ほんわかした声質。テンションは高くない。声は高い。'


@functools.lru_cache(maxsize=1)
def get_tts_client():
    info = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(info)
    return texttospeech.TextToSpeechClient(credentials=credentials)


def add_gap_minutes(timeline):
    for schedule, following_schedule in zip(timeline, timeline[1:], strict=False):
        gap_time = following_schedule.start_at - schedule.end_at
        gap = int(gap_time.total_seconds() / 60)
        if gap > 0:
            schedule.gap_minutes = gap


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        context['today'] = today
        schedules = Schedule.objects.filter(user=self.request.user, start_at__date=today).order_by('start_at')
        context['schedules'] = schedules

        now = timezone.now()
        context['now'] = now
        state, current_schedule, next_schedule = get_schedule_status(schedules, now)
        context['state'] = state
        context['current_schedule'] = current_schedule
        context['next_schedule'] = next_schedule

        timeline = list(schedules)
        add_gap_minutes(timeline)
        context['timeline'] = timeline

        return context

@method_decorator(never_cache, name='dispatch')
class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/input.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        usage = get_today_usage(self.request.user, today)
        context['remaining'] = get_remaining(usage)

        mode = self.request.GET.get('mode')
        from_value = self.request.GET.get('from')
        if from_value == 'run':
            return_url = reverse('schedules:task_run')
        elif mode:
            return_url = reverse('schedules:edit')
        else:
            return_url = reverse('schedules:dashboard')
        context['return_url'] = return_url

        schedules = Schedule.objects.filter(user=self.request.user, start_at__date=today)
        schedules_list = []
        for schedule in schedules:
            s_dict = {
                'title': schedule.title,
                'start_at': schedule.start_at,
                'end_at': schedule.end_at,
                'is_new': False
            }
            schedules_list.append(s_dict)
        if (mode == 'add' or mode == 'edit') and self.request.session.get('new_schedules_date') == today.isoformat():
            new_schedules = self.request.session.get('new_schedules', [])
            for new_schedule in new_schedules:
                new_s_dict = {
                    'title': new_schedule['title'],
                    'start_at': datetime.fromisoformat(new_schedule['start_at']),
                    'end_at': datetime.fromisoformat(new_schedule['end_at']),
                    'is_new': True
                }
                schedules_list.append(new_s_dict)
        schedules_list =  sorted(schedules_list, key=lambda s: s['start_at'])
        now = timezone.now()
        for schedule in schedules_list:
            schedule['duration_minutes'] = int((schedule['end_at'] - schedule['start_at']).total_seconds() / 60)
            schedule['is_finished'] = False
            if schedule['end_at'] <= now:
                schedule['is_finished'] = True
            schedule['is_current'] = False
            if schedule['start_at'] <= now and schedule['end_at'] > now:
                schedule['is_current'] = True
        for schedule, following_schedule in zip(schedules_list, schedules_list[1:], strict=False):
            gap_time = following_schedule['start_at'] - schedule['end_at']
            gap = int(gap_time.total_seconds() / 60)
            if gap > 0:
                schedule['gap_minutes'] = gap
        context['schedules'] = schedules_list
        context['mode'] = mode
        return context

class SpeechView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        text = data.get('text', '')
        if not text.strip() or len(text) > SPEECH_MAX_LENGTH:
            return JsonResponse({'error': '文が空か、長すぎるよ'}, status=400)

        if not settings.GOOGLE_CREDENTIALS_JSON:
            return JsonResponse({'error': 'APIが設定されていないよ'}, status=503)
        try:
            response = get_tts_client().synthesize_speech(
                input=texttospeech.SynthesisInput(
                    text=text,
                    prompt=SPEECH_STYLE_PROMPT,
                ),
                voice=texttospeech.VoiceSelectionParams(
                    language_code='ja-JP',
                    name=settings.GOOGLE_TTS_VOICE,
                    model_name=settings.GOOGLE_TTS_MODEL,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                ),
                timeout=6.0,
            )
        except GoogleAPIError as error:
            print('GoogleTTS error:', repr(error))
            return JsonResponse({'error': 'GoogleTTSとの接続がうまくいかなかったよ'}, status=502)

        return HttpResponse(response.audio_content, content_type='audio/mpeg')

@method_decorator(never_cache, name='dispatch')
class KeepAliveView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(status=204)
        

class TranscriptView(LoginRequiredMixin, View):
    def post(self, request):
        data = json.loads(request.body)
        text = data.get('text', '')
        mode = data.get('mode')

        if not text.strip():
            return JsonResponse({'error': 'うまく聞き取れなかったよ。もう一度話してね。'}, status=400)
        
        now = timezone.localtime()
        today = now.date()
        usage = get_today_usage(request.user, today)
        current_schedules = None
        if mode == 'edit':
            if request.session.get('new_schedules_date') == today.isoformat():
                current_schedules = request.session.get('new_schedules', [])
            if not current_schedules:
                return JsonResponse({'error': '直せる予定がないよ'}, status=400)

        if usage.count >= settings.AI_DAILY_LIMIT:
            return JsonResponse({'error': '今日は5回使ったよ。また明日話してね。'}, status=429)
        
        try:
            result = ask_ai(text, now, current_schedules=current_schedules)
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

@method_decorator(never_cache, name='dispatch')
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
            formset=BaseScheduleFormSet,
            extra=len(new_schedules),
            can_delete=True
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
            if request.POST.get('action') == 'save':
                messages.success(request, '予定を保存したよ')
                return redirect('schedules:edit')
            return redirect('schedules:task_run')
        context = self.get_context_data()
        context['formset'] = formset
        return self.render_to_response(context)

class ScheduleClearView(LoginRequiredMixin, View):
    def post(self, request):
        today = timezone.localdate()
        Schedule.objects.filter(user=request.user, start_at__date=today).delete()
        request.session.pop('new_schedules', None)
        request.session.pop('new_schedules_date', None)
        return redirect(f"{reverse('schedules:input')}?mode=restart")

class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        schedules = Schedule.objects.filter(
            user=self.request.user, start_at__date=today
        ).order_by('start_at')
        context['schedules'] = schedules

        schedules_list = []
        for schedule in schedules:
            s = {
                'id': schedule.pk,
                'title': schedule.title,
                'start_at': schedule.start_at,
                'end_at': schedule.end_at,
            }
            schedules_list.append(s)
        context['schedules_list'] = schedules_list

        now = timezone.now()
        state, current_schedule, next_schedule = get_schedule_status(schedules, now)
        context['state'] = state
        context['current_schedule'] = current_schedule
        context['next_schedule'] = next_schedule

        timeline = list(schedules)
        add_gap_minutes(timeline)
        context['timeline'] = timeline

        setting, created = Setting.objects.get_or_create(user=self.request.user)
        settings_data = {
            'time_left_alert': setting.time_left_alert,
            'alert_interval': setting.alert_interval,
        }
        context['settings_data'] = settings_data
        return context

class StartNowView(LoginRequiredMixin, View):
    def post(self, request):
        today = timezone.localdate()
        data = json.loads(request.body)
        schedule_id = data['id']
        schedules = Schedule.objects.filter(
            user=self.request.user, start_at__date=today
        ).order_by('start_at')

        now = timezone.now()
        state, current_schedule, next_schedule = get_schedule_status(schedules, now)
        if state == 'waiting' or state == 'soon':
            if schedule_id == next_schedule.pk:
                next_schedule.start_at = now
                next_schedule.save()
                return JsonResponse({'start_at': next_schedule.start_at})
        messages.error(request, '予定が変わっていたので、表示しなおしたよ。もう一度試してみてね')
        return JsonResponse({}, status=400)

# TODO: 設定画面の Issue で UpdateView に作り替える
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
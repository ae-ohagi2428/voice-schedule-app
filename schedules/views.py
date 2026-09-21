from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, UpdateView
from django.utils import timezone

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.localdate()
        return context

class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/schedule_input.html'

class ScheduleEditView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_edit.html'

class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_update.html'

class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'

# TODO: 設定画面の Issue で UpdateView に作り替える
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, UpdateView

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/schedule_input.html'

class ScheduleEditView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_edit.html'

class ScheduleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/schedule_update.html'

class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'

class SettingsView(LoginRequiredMixin, UpdateView):
    template_name = 'schedules/settings.html'
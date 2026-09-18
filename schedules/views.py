from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, UpdateView
from django.urls import reverse_lazy
from datetime import date, timedelta

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/dashboard.html'

class ScheduleInputView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/schedule_input.html'

# ↓後でUpdateViewになおす
class ScheduleEditView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/schedule_edit.html'

# ↓後でDetailViewになおす
class TaskRunView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/task_run.html'

# あとでUpdateViewになおす
class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/settings.html'
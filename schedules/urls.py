from django.urls import path
from .views import DashboardView, ScheduleInputView, ScheduleEditView, ScheduleUpdateView, TaskRunView, SettingsView

app_name = 'schedules'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('input/', ScheduleInputView.as_view(), name='input'),
    path('edit/', ScheduleEditView.as_view(), name='schedule_edit'),
    path('<int:pk>/edit/', ScheduleUpdateView.as_view(), name='schedule_update'),
    path('task_run/', TaskRunView.as_view(), name='task_run'),
    path('settings/', SettingsView.as_view(), name='settings'),
]
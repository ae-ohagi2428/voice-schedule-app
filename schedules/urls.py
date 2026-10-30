from django.urls import path

from .views import (
    DashboardView,
    KeepAliveView,
    ScheduleClearView,
    ScheduleEditView,
    ScheduleInputView,
    SettingsView,
    SpeechView,
    StartNowView,
    TaskRunView,
    TranscriptView,
)

app_name = 'schedules'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('input/', ScheduleInputView.as_view(), name='input'),
    path('edit/', ScheduleEditView.as_view(), name='edit'),
    path('speech/', SpeechView.as_view(), name='speech'),
    path('keep_alive/', KeepAliveView.as_view(), name='keep_alive'),
    path('clear/', ScheduleClearView.as_view(), name='clear'),
    path('task_run/', TaskRunView.as_view(), name='task_run'),
    path('task_run/start_now/', StartNowView.as_view(), name='start_now'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('input/transcript/', TranscriptView.as_view(), name='transcript'),
]
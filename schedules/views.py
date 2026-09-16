from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, UpdateView

class DashboardView(TemplateView):
    
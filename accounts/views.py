from schedules.models import Setting
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import LoginForm, RegistrationForm


class RegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('schedules:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        Setting.objects.create(user=self.object)
        login(self.request, self.object)
        messages.success(self.request, '登録が完了しました')
        return response

    

class LoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self,form):
        messages.success(self.request, 'ログインしました')
        return super().form_valid(form)

class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy('accounts:login')

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'ログアウトしました')
        return super().post(request, *args, **kwargs)

class EmailChangeView(LoginRequiredMixin, UpdateView):
    success_url = reverse_lazy('schedules:settings')
    template_name = 'accounts/email_change.html'

    def form_valid(self,form):
        messages.success(self.request, 'メールアドレスを変更しました')
        return super().form_valid(form)

class PasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    success_url = reverse_lazy('schedules:settings')
    template_name = 'accounts/password_change.html'

    def form_valid(self,form):
        messages.success(self.request, 'パスワードを変更しました')
        return super().form_valid(form)

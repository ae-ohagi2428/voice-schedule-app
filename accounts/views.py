from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView, PasswordChangeView as DjangoPasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView, TemplateView
# from .forms import EmailAuthenticationForm, RegistrationForm

# あとでFormViewになおす
class RegisterView(TemplateView):
    template_name = 'accounts/register.html'
    # form_class = RegistrationForm
    success_url = reverse_lazy('schedules:dashboard')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, '登録が完了しました')
        return super().form_valid(form)

# あとでDjangoLoginViewになおす
class LoginView(TemplateView):
    template_name = 'accounts/login.html'
    # authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self,form):
        messages.success(self.request, 'ログインしました')
        return super().form_valid(form)

# あとでDjangoLoginViewになおす
class LogoutView(TemplateView):
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'ログアウトしました')
        return super().dispatch(request, *args, **kwargs)

# あとでUpdateViewになおす
class EmailChangeView(LoginRequiredMixin, TemplateView):
    success_url = reverse_lazy('schedules:settings')
    template_name = 'accounts/email_change.html'

    def form_valid(self,form):
        messages.success(self.request, 'メールアドレスを変更しました')
        return super().form_valid(form)

# あとでDjangoPasswordChangeViewになおす
class PasswordChangeView(LoginRequiredMixin, TemplateView):
    success_url = reverse_lazy('schedules:settings')
    template_name = 'accounts/password_change.html'

    def form_valid(self,form):
        messages.success(self.request, 'パスワードを変更しました')
        return super().form_valid(form)

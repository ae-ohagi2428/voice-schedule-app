from django.urls import path
from .views import RegisterView, LoginView, EmailChangeView, PasswordChangeView

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LoginView.as_view(), name='logout'),
    path('email_change/', EmailChangeView.as_view(), name='email_change'),
    path('password_change/', PasswordChangeView.as_view(), name='password_change'),
]
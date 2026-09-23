from django.urls import path

from .views import HomeView, PrivacyPolicyView, TermsofServiceView

app_name = 'home'

urlpatterns = [
    path('', HomeView.as_view(), name='index'),
    path('terms_of_service/', TermsofServiceView.as_view(), name='terms_of_service'),
    path('privacy_policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]
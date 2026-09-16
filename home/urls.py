from django.urls import path
from .views import HomeView, TermsofServiceView, PrivacyPolicyView

app_name = 'home'

urlpatterns = [
    path('index/', HomeView.as_view(), name='index'),
    path('terms_of_service/', TermsofServiceView.as_view(), name='terms_of_service'),
    path('pricacy_policy/', PrivacyPolicyView.as_view(), name='pricacy_policy'),
]
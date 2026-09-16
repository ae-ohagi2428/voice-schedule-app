from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'home/index.html'

class TermsofServiceView(TemplateView):
    template_name = 'home/terms_of_service.html'

class PrivacyPolicyView(TemplateView):
    template_name = 'home/pricacy_policy.html'
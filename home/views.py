from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'home/index.html'

class TermsView(TemplateView):
    template_name = 'home/terms_of_service.html'

class PrivacyView(TemplateView):
    template_name = 'home/pricacy_policy.html'
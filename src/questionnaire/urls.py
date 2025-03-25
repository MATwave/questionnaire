from django.urls import path
from .views import home_view, user_profile_view, questionnaire_view, thank_you_view

urlpatterns = [
    path('', home_view, name='home'),
    path('profile/', user_profile_view, name='user_profile_view'),
    path('survey/', questionnaire_view, name='questionnaire_start'),
    path('survey/<int:question_order>/', questionnaire_view, name='questionnaire_view'),
    path('thank-you/', thank_you_view, name='thank_you_view'),
]
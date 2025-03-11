from django.urls import path
from .views import questionnaire_list, user_profile_view, questionnaire_view, thank_you_view

urlpatterns = [
    path('', questionnaire_list, name='questionnaire_list'),
    path('<int:questionnaire_id>/profile/', user_profile_view, name='user_profile_view'),
    path('<int:questionnaire_id>/', questionnaire_view, name='questionnaire_view'),
    path('<int:questionnaire_id>/question/<int:question>/', questionnaire_view, name='questionnaire_view_with_question'),
    path('thank-you/', thank_you_view, name='thank_you_view'),
]
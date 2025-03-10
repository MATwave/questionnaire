from django.urls import path
from . import views

urlpatterns = [
    path('<int:questionnaire_id>/', views.questionnaire_view, name='questionnaire_view'),
]

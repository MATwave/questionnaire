# scripts/fill_survey_ratings.py
import os
import django
import sys

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from questionnaire.models import SurveyResult, AnonymousUserProfile, UserResponse
from questionnaire.utils import calculate_user_rating
from django.db import transaction


def fill_all_ratings():
    """Заполняет calculated_rating для всех SurveyResult"""
    print("Начинаем заполнение рейтингов...")

    # Вариант 2: Создаем SurveyResult для старых данных
    profiles_without_result = AnonymousUserProfile.objects.filter(
        filled_survey=True
    ).exclude(
        survey_result__isnull=False
    )

    print(f"Найдено {profiles_without_result.count()} профилей без SurveyResult")

    for i, profile in enumerate(profiles_without_result, 1):
        try:
            with transaction.atomic():
                # Получаем первый ответ для даты
                first_response = UserResponse.objects.filter(
                    user_profile=profile
                ).earliest('created_at')

                # Формируем responses_data
                responses_data = {
                    'profile_info': {
                        'gender': profile.gender,
                        'age': profile.age,
                        'height': profile.height,
                        'weight': profile.weight
                    },
                    'questions': []
                }

                # Собираем все ответы
                user_responses = UserResponse.objects.filter(
                    user_profile=profile
                ).select_related('question').prefetch_related('selected_answers')

                for response in user_responses:
                    question_data = {
                        'question_id': response.question.id,
                        'question_text': response.question.text,
                        'question_order': response.question.order,
                        'free_text_answer': response.free_text_answer or '',
                        'numeric_answer': response.numeric_answer,
                        'selected_answers': []
                    }

                    for answer in response.selected_answers.all():
                        question_data['selected_answers'].append({
                            'answer_id': answer.id,
                            'answer_text': answer.text,
                            'value': float(answer.value) if answer.value is not None else 0.0,
                            'recommendation': answer.recommendation or ''
                        })

                    responses_data['questions'].append(question_data)

                # Рассчитываем рейтинг
                rating_data = calculate_user_rating(profile)

                # Создаем SurveyResult
                SurveyResult.objects.create(
                    user_profile=profile,
                    responses_data=responses_data,
                    calculated_rating=rating_data,
                    created_at=first_response.created_at
                )

                if i % 10 == 0:
                    print(f"Создано {i} новых SurveyResult")

        except Exception as e:
            print(f"Ошибка для профиля {profile.id}: {e}")

    print("Заполнение рейтингов завершено!")


if __name__ == '__main__':
    fill_all_ratings()
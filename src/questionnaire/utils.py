from django.db.models import Prefetch
from .models import Question, UserResponse, Answer


def get_question_categories():
    """Возвращает категории вопросов с их описаниями и метками"""
    return {
        'stress': {
            'description': "СТРЕСС",
            'label': 'СТРЕСС'
        },
        'nutrition': {
            'description': "ПИТАНИЕ",
            'label': 'ПИТАНИЕ'
        },
        'eating_behavior': {
            'description': "Как часто Вы употребляете следующие продукты и напитки",
            'label': 'Пищевое поведение'
        },
        'work_assessment': {
            'description': "САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА",
            'label': 'Самооценка труда'
        }
    }


def calculate_user_rating(user_profile):
    """Расчет рейтинга с оптимизированными запросами к БД"""
    categories = get_question_categories()

    # Оптимизация запросов через prefetch_related
    responses = UserResponse.objects.filter(
        user_profile=user_profile
    ).prefetch_related(
        Prefetch('selected_answers', queryset=Answer.objects.only('value')),
        'question'
    )

    # Инициализация словаря для сбора значений
    category_values = {key: [] for key in categories}

    # Собираем значения ответов по категориям
    for response in responses:
        category = next(
            (key for key, params in categories.items()
             if response.question.description == params['description']),
            None
        )

        if category:
            values = [a.value for a in response.selected_answers.all() if a.value is not None]
            category_values[category].extend(values)

    # Расчет средних значений
    def safe_avg(values):
        return sum(values) / len(values) if values else 0

    results = {f'{key}_avg': safe_avg(vals) for key, vals in category_values.items()}

    # Расчет общего балла
    total_values = [v for v in results.values() if v > 0]
    results['total_score'] = safe_avg(total_values) if total_values else 0

    # Определение рейтинга
    if results['total_score'] <= 0.47:
        results['rating'] = "Неудовлетворительная"
    elif results['total_score'] <= 0.67:
        results['rating'] = "Удовлетворительная"
    elif results['total_score'] <= 0.89:
        results['rating'] = "Хорошая"
    else:
        results['rating'] = "Оптимальная"

    return results
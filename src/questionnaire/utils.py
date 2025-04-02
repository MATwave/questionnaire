from django.db.models import Prefetch
from .models import Question, UserResponse, Answer


def get_question_categories():
    """Возвращает категории вопросов с их описаниями и метками"""
    return {
        'stress': {
            'descriptions': ["СТРЕСС"],
            'label': 'СТРЕСС'
        },
        'nutrition': {
            'descriptions': ["ПИТАНИЕ"],
            'label': 'ПИТАНИЕ'
        },
        'eating_behavior': {
            'descriptions': ["Как часто Вы употребляете следующие продукты и напитки"],
            'label': 'Пищевое поведение'
        },
        'work_assessment': {
            'descriptions': ["САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА"],
            'label': 'Самооценка труда'
        },
        'lifestyle': {
            'descriptions': ["ОБРАЗ ЖИЗНИ И РЕЖИМ ДНЯ", "Курение (сигарет в день)", "Курение (лет стажа)"],
            'label': 'Образ жизни и ФАиРД'
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
        Prefetch('question', queryset=Question.objects.only('description'))
    )

    # Если нет ни одного ответа
    if not responses.exists():
        return {
            'stress_avg': 0.0,
            'nutrition_avg': 0.0,
            'eating_behavior_avg': 0.0,
            'work_assessment_avg': 0.0,
            'lifestyle_avg': 0.0,
            'total_score': 0.0,
            'rating': 'Нет данных'
        }

    # Инициализация словаря для сбора значений
    category_values = {key: [] for key in categories}
    smoking_data = {'cigarettes': 0, 'years': 0}

    # Собираем значения ответов по категориям
    for response in responses:
        category = next(
            (key for key, params in categories.items()
             if response.question.description in params['descriptions']),
            None
        )

        if category:
            if category == 'lifestyle':
                # Собираем данные для расчета индекса курильщика
                if response.question.description == "Курение (сигарет в день)":
                    smoking_data['cigarettes'] = sum(a.value for a in response.selected_answers.all())
                elif response.question.description == "Курение (лет стажа)":
                    smoking_data['years'] = sum(a.value for a in response.selected_answers.all())
                else:
                    values = [a.value for a in response.selected_answers.all() if a.value is not None]
                    category_values['lifestyle'].extend(values)
            else:
                values = [a.value for a in response.selected_answers.all() if a.value is not None]
                category_values[category].extend(values)

    # Расчет индекса курильщика
    if smoking_data['cigarettes'] > 0 and smoking_data['years'] > 0:
        smoking_index = (smoking_data['cigarettes'] * smoking_data['years']) / 20
        # Добавляем индекс курильщика как отдельный показатель
        category_values['lifestyle'].append(min(smoking_index, 1.0))

    # Нормализация значений для категории lifestyle
    if category_values['lifestyle']:
        # Ограничиваем максимальное значение до 1.0 для всех элементов
        category_values['lifestyle'] = [min(val, 1.0) for val in category_values['lifestyle']]

    # Расчет средних значений
    def safe_avg(values):
        return round(sum(values) / len(values), 4) if values else 0.0

    results = {f'{key}_avg': safe_avg(vals) for key, vals in category_values.items()}

    # Расчет общего балла (только по категориям с данными)
    total_values = [v for v in results.values() if v > 0]
    results['total_score'] = safe_avg(total_values) if total_values else 0.0

    # Определение рейтинга
    if results['total_score'] <= 0.47:
        results['rating'] = "Неудовлетворительная"
    elif results['total_score'] <= 0.67:
        results['rating'] = "Удовлетворительная"
    elif results['total_score'] <= 0.89:
        results['rating'] = "Хорошая"
    else:
        results['rating'] = "Оптимальная"

    # Округляем значения для вывода
    for key in results:
        if isinstance(results[key], float):
            results[key] = round(results[key], 2)

    return results
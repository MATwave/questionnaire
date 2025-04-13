from django.db.models import Prefetch
from .models import Question, UserResponse, Answer


def get_question_categories():
    """Конфигурация категорий вопросов"""
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
            'descriptions': [
                "ОБРАЗ ЖИЗНИ И РЕЖИМ ДНЯ",
                "Курение (сигарет в день)",
                "Курение (лет стажа)"
            ],
            'label': 'Образ жизни и ФАиРД'
        },
            'medico_biological': {
            'descriptions': ["МЕДИКО-БИОЛОГИЧЕСКИЕ ФАКТОРЫ",
                             "Имеющиеся заболевания"],
            'label': 'Медико-биологические факторы'
        }

    }


def calculate_user_rating(user_profile):
    """Основная функция расчета рейтинга"""
    # Инициализация базового результата
    result = initialize_base_result()

    # Получение ответов пользователя
    responses = get_user_responses(user_profile)
    if not responses.exists():
        return result

    # Расчет данных ИМТ
    bmi_data = calculate_bmi_data(user_profile)

    # Обработка ответов и категорий
    category_values, smoking_data, diseases = process_responses(responses, bmi_data)

    # Расчет средних значений по категориям
    category_averages = calculate_category_averages(category_values)

    # Расчет общего балла
    total_score = calculate_total_score(category_averages)

    # Обновление результата
    update_result(
        result,
        bmi_data,
        category_averages,
        total_score,
        smoking_data,
        diseases
    )

    return result


def initialize_base_result():
    """Инициализация базовой структуры результата"""
    return {
        'medico_biological_avg': 0.0,
        'stress_avg': 0.0,
        'nutrition_avg': 0.0,
        'eating_behavior_avg': 0.0,
        'work_assessment_avg': 0.0,
        'lifestyle_avg': 0.0,
        'total_score': 0.0,
        'rating': 'Нет данных',
        'bmi': 'Нет данных',
        'bmi_category': 'Не рассчитан',
        'bmi_risk_level': 'Не определен',
        'bmi_risk_description': 'Данные для оценки рисков отсутствуют'
    }


def get_user_responses(user_profile):
    """Получение ответов пользователя с префетчингом"""
    return UserResponse.objects.filter(
        user_profile=user_profile
    ).prefetch_related(
        Prefetch('selected_answers', queryset=Answer.objects.only('value')),
        Prefetch('question', queryset=Question.objects.only('description'))
    )


def calculate_bmi_data(user_profile):
    """Расчет данных ИМТ"""
    bmi_data = {
        'value': None,
        'category': 'Не рассчитан',
        'risk_level': 'Не определен',
        'risk_description': 'Данные для расчета отсутствуют'
    }

    if not (user_profile.height and user_profile.weight):
        return bmi_data

    try:
        height_m = user_profile.height / 100
        bmi_value = user_profile.weight / (height_m ** 2)
        bmi_data['value'] = round(bmi_value, 1)

        # Определение категории ИМТ
        bmi_categories = get_bmi_categories()
        for category in bmi_categories:
            if category['matches'](bmi_value):
                bmi_data.update({
                    'category': category['name'],
                    'risk_level': category['risk_level'],
                    'risk_description': category['description']
                })
                break

    except (ZeroDivisionError, TypeError):
        pass

    return bmi_data


def get_bmi_categories():
    """Конфигурация категорий ИМТ и связанных с ними рисков"""
    return [
        # Ожирение III степени
        {
            'min': 40.0,
            'max': None,
            'name': "Ожирение III ст.",
            'risk_level': "Крайне высокий риск заболеваний",
            'description': (
                "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
                "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
                "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
                "опорно-двигательного аппарата, онкологических заболеваний)"
            ),
            'matches': lambda x: x >= 40.0
        },
        # Ожирение II степени
        {
            'min': 35.0,
            'max': 39.9,
            'name': "Ожирение II ст.",
            'risk_level': "Очень высокий риск заболеваний",
            'description': (
                "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
                "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
                "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
                "опорно-двигательного аппарата, онкологических заболеваний)"
            ),
            'matches': lambda x: 35.0 <= x <= 39.9
        },
        # Ожирение I степени
        {
            'min': 30.0,
            'max': 34.9,
            'name': "Ожирение I ст.",
            'risk_level': "Высокий риск заболеваний",
            'description': (
                "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
                "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
                "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
                "опорно-двигательного аппарата, онкологических заболеваний)"
            ),
            'matches': lambda x: 30.0 <= x <= 34.9
        },
        # Избыточная масса тела
        {
            'min': 25.0,
            'max': 29.9,
            'name': "Избыточная масса тела",
            'risk_level': "Повышенный риск заболеваний",
            'description': "у вас повышен риск развития заболеваний, связанных с избыточным питанием",
            'matches': lambda x: 25.0 <= x <= 29.9
        },
        # Нормальный ИМТ
        {
            'min': 18.5,
            'max': 24.9,
            'name': "Нормальный ИМТ",
            'risk_level': "Риск снижен",
            'description': "Риск сопутствующих заболеваний снижен",
            'matches': lambda x: 18.5 <= x <= 24.9
        },
        # Недостаточность питания I степени
        {
            'min': 17.0,
            'max': 18.49,
            'name': "Недостаточность питания I ст.",
            'risk_level': "Повышенный риск",
            'description': (
                "У вас повышен риск развития заболеваний, связанных с недостаточным питанием"
            ),
            'matches': lambda x: 17.0 <= x <= 18.49
        },
        # Недостаточность питания II степени
        {
            'min': 16.0,
            'max': 16.9,
            'name': "Недостаточность питания II ст.",
            'risk_level': "Высокий риск",
            'description': (
                "У вас наблюдается высокий риск заболеваний, связанных с недостаточным питанием, - "
                "белковая, белково-энергетическая недостаточность (истощение, кахексия), "
                "вследствие снижения резистентности организма к инфекционных и неинфекционным "
                "факторам высокая вероятность инфекционных заболеваний, болезней органов пищеварения"
            ),
            'matches': lambda x: 16.0 <= x <= 16.9
        },
        # Недостаточность питания III степени
        {
            'min': 0.0,
            'max': 15.9,
            'name': "Недостаточность питания III ст.",
            'risk_level': "Критический риск",
            'description': (
                "У вас наблюдается высокий риск заболеваний, связанных с недостаточным питанием, - "
                "белковая, белково-энергетическая недостаточность (истощение, кахексия), "
                "вследствие снижения резистентности организма к инфекционных и неинфекционным "
                "факторам высокая вероятность инфекционных заболеваний, болезней органов пищеварения"
            ),
            'matches': lambda x: 0.0 <= x <= 15.9
        }
    ]


def process_responses(responses, bmi_data):
    """Обработка ответов пользователя"""
    categories = get_question_categories()
    category_values = {key: [] for key in categories}
    smoking_data = {'cigarettes': 0, 'years': 0}
    diseases = []

    # 1. Обработка обычных ответов
    for response in responses:
        category = get_response_category(response, categories)
        if not category:
            continue

        values = get_answer_values(response)

        if response.question.description == "Имеющиеся заболевания":
            diseases.extend([a.text for a in response.selected_answers.all()])
            if response.free_text_answer:
                diseases.append(response.free_text_answer)

        if category == 'lifestyle':
            handle_lifestyle_response(response, values, smoking_data, category_values)
        else:
            category_values[category].extend(values)

    # 2. Добавляем индекс курильщика
    if smoking_data['cigarettes'] > 0 and smoking_data['years'] > 0:
        smoking_index = (smoking_data['cigarettes'] * smoking_data['years']) / 20
        category_values['lifestyle'].append(min(smoking_index, 1.0))

    # 3. Добавляем ИМТ как отдельный показатель
    medico_bio_value = 1.0 if bmi_data.get('category') == 'Нормальный ИМТ' else 0.0
    category_values.setdefault('medico_biological', []).append(medico_bio_value)

    return category_values, smoking_data, diseases


def get_response_category(response, categories):
    """Определение категории для ответа"""
    for key, params in categories.items():
        if response.question.description in params['descriptions']:
            return key
    return None


def get_answer_values(response):
    """Получение значений ответов"""
    return [a.value for a in response.selected_answers.all() if a.value is not None]


def handle_lifestyle_response(response, values, smoking_data, category_values):
    """Обработка ответов категории lifestyle"""
    desc = response.question.description
    if desc == "Курение (сигарет в день)":
        smoking_data['cigarettes'] = sum(values)
    elif desc == "Курение (лет стажа)":
        smoking_data['years'] = sum(values)
    else:
        category_values['lifestyle'].extend(values)


def calculate_category_averages(category_values):
    """Расчет средних"""
    averages = {}
    for category, values in category_values.items():
        # Для lifestyle применяем нормализацию
        if category == 'lifestyle':
            values = [min(val, 1.0) for val in values]

        avg = safe_average(values) if values else 0.0
        averages[f'{category}_avg'] = avg

    return averages


def process_lifestyle_values(values):
    """Обработка значений для категории lifestyle"""
    return [min(val, 1.0) for val in values]


def safe_average(values):
    """Безопасный расчет среднего"""
    return round(sum(values) / len(values), 4) if values else 0.0


def calculate_total_score(averages):
    """Расчет общего балла"""
    total_values = [v for v in averages.values() if v > 0]
    return safe_average(total_values) if total_values else 0.0


def determine_rating(total_score):
    """Определение рейтинга"""
    if total_score <= 0.47:
        return "Неудовлетворительная"
    elif total_score <= 0.67:
        return "Удовлетворительная"
    elif total_score <= 0.89:
        return "Хорошая"
    return "Оптимальная"


def update_result(result, bmi_data, category_averages, total_score, smoking_data, diseases):
    """Обновление итогового результата"""
    # Обновление категорий
    result.update(category_averages)

    # Обновление ИМТ
    result.update({
        'bmi': bmi_data.get('value', 'Нет данных'),
        'bmi_category': bmi_data.get('category', 'Не рассчитан'),
        'bmi_risk_level': bmi_data.get('risk_level', 'Не определен'),
        'bmi_risk_description': bmi_data.get('risk_description', 'Данные отсутствуют'),
        'existing_diseases': diseases if diseases else None
    })

    # Общие показатели
    result['total_score'] = round(total_score, 2)
    result['rating'] = determine_rating(total_score)

    # Округление значений
    for key in result:
        if isinstance(result[key], float):
            result[key] = round(result[key], 2)
from django.db import transaction
from django.db.models import Prefetch
from .models import Question, UserResponse, Answer, SurveyResult

# TODO: сейчас это все рассчитывается по всем, хотя можно по пользователю, что снизит нагрузку

# Константы для категорий вопросов
QUESTION_CATEGORIES = {
    'stress': {
        'descriptions': ["СТРЕСС"],
        'label': 'СТРЕСС'
    },
    'nutrition': {
        'descriptions': [
            "ПИТАНИЕ", "ПРИЕМЫ ПИЩИ", "ВРЕМЯ ПЕРЕРЫВОВ МЕЖДУ ЕДОЙ", "ЗАВТРАК",
            "НАИБОЛЕЕ ПЛОТНЫЙ ПРИЕМ ПИЩИ", "ЕДА ДО СНА", "ВИД ЖИРОВ", "ГОЛОД",
            "ЭМОЦИОНАЛЬНЫЕ ПЕРЕКУСЫ", "ПООЩРЕНИЕ ИЛИ НАКАЗАНИЕ ЕДОЙ"
        ],
        'label': 'ПИТАНИЕ'
    },
    'eating_behavior': {
        'descriptions': [
            "ПИЩЕВОЕ ПОВЕДЕНИЕ", "СНЕКИ", "ФАСТ-ФУД", "СЛАДКАЯ ГАЗИРОВКА",
            "КОЛБАСНЫЕ ИЗДЕЛИЯ", "КОПЧЕНЫЕ ПРОДУКТЫ", "ПИЩЕВЫЕ ЖИРЫ", "СОУСЫ",
            "ЖАРЕННЫЙ КАРТОФЕЛЬ", "СОЛЕНЫЕ И КОНСЕРВИРОВАННЫЕ ПРОДУКТЫ",
            "МОЛОЧНЫЕ ПРОДУКТЫ С ВЫСОКОЙ ЖИРНОСТЬЮ", "ВЫПЕЧКА",
            "КОЛИЧЕСТВО ФРУКТОВ И ОВОЩЕЙ", "ЗЛАКОВЫЕ ПРОДУКТЫ", "БОБОВЫЕ",
            "НЕЖИРНОЕ МЯСО", "РЫБА И МОРЕПРОДУКТЫ", "МОЛОКО И КИСЛОМОЛОЧКА",
            "РАСТИТЕЛЬНЫЕ МАСЛА", "ЖИДКОСТЬ В ДЕНЬ", "ДОСАЛИВАНИЕ",
            "СПЕЦИАЛЬНАЯ ПИЩЕВАЯ ПРОДУКЦИЯ", "БАДЫ"
        ],
        'label': 'Пищевое поведение'
    },
    'work_assessment': {
        'descriptions': [
            "САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА", "РАБОЧЕЕ МЕСТО", "ФИЗИЧЕСКИЕ НАГРУЗКИ",
            "ТЕМП РАБОТЫ", "ЭМОЦИОНАЛЬНАЯ НАГРУЗКА", "УТОМЛЯЕМОСТЬ", "ГРАФИК РАБОТЫ",
            "ТРУД С ЦИФРОВЫМИ УСТРОЙСТВАМИ", "КРИТИЧЕСКИЕ СИТУАЦИИ", "ЭКСТРА УСИЛИЯ",
            "РЕГЛАМЕНТИРОВАННЫЕ ПЕРЕРЫВЫ", "ОБЕДЕННЫЙ ПЕРЕРЫВ", "РАБОТА НА ДОМУ"
        ],
        'label': 'Самооценка труда'
    },
    'lifestyle': {
        'descriptions': [
            "ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ", "СОН", "ЦИФРОВАЯ ГИГИЕНА", "ОТПУСК", "АЛКОГОЛЬ",
            "ОБРАЗ ЖИЗНИ И РЕЖИМ ДНЯ", "Курение (сигарет в день)", "Курение (лет стажа)"
        ],
        'label': 'Образ жизни и ФАиРД'
    },
    'medico_biological': {
        'descriptions': [
            "МЕДИКО-БИОЛОГИЧЕСКИЕ ФАКТОРЫ", "Имеющиеся заболевания", "ОКРУЖНОСТЬ (ТАЛИИ)",
            "ОКРУЖНОСТЬ (БЕДЕР)", "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ", "ОБЩИЙ ХОЛЕСТЕРИН", "УРОВЕНЬ ГЛЮКОЗЫ"
        ],
        'label': 'Медико-биологические факторы'
    }
}

def get_question_categories():
    """Возвращает конфигурацию категорий вопросов (для совместимости с тестами)"""
    return QUESTION_CATEGORIES

# Категории ИМТ и связанные с ними риски
BMI_CATEGORIES = [
    {
        'min': 18.5, 'max': 24.9, 'name': "Нормальный ИМТ",
        'risk_level': "Риск снижен",
        'description': "Риск сопутствующих заболеваний снижен",
        'matches': lambda x: 18.5 <= x <= 24.9
    },
    {
        'min': 25.0, 'max': 29.9, 'name': "Избыточная масса тела",
        'risk_level': "Повышенный риск заболеваний",
        'description': "у вас повышен риск развития заболеваний, связанных с избыточным питанием",
        'matches': lambda x: 25.0 <= x <= 29.9
    },
    {
        'min': 30.0, 'max': 34.9, 'name': "Ожирение I ст.",
        'risk_level': "Высокий риск заболеваний",
        'description': (
            "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
            "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
            "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
            "опорно-двигательного аппарата, онкологических заболеваний)"
        ),
        'matches': lambda x: 30.0 <= x <= 34.9
    },
    {
        'min': 35.0, 'max': 39.9, 'name': "Ожирение II ст.",
        'risk_level': "Очень высокий риск заболеваний",
        'description': (
            "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
            "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
            "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
            "опорно-двигательного аппарата, онкологических заболеваний)"
        ),
        'matches': lambda x: 35.0 <= x <= 39.9
    },
    {
        'min': 40.0, 'max': None, 'name': "Ожирение III ст.",
        'risk_level': "Крайне высокий риск заболеваний",
        'description': (
            "У вас наблюдается высокий риск заболеваний, связанных с повышенным питанием "
            "(сердечно-сосудистой системы - артериальной гипертензии, эндокринной системы - "
            "сахарного диабета, пищеварительной системы - желчно-каменной болезни, "
            "опорно-двигательного аппарата, онкологических заболеваний)"
        ),
        'matches': lambda x: x >= 40.0
    },
    {
        'min': 17.0, 'max': 18.49, 'name': "Недостаточность питания I ст.",
        'risk_level': "Повышенный риск",
        'description': "У вас повышен риск развития заболеваний, связанных с недостаточным питанием",
        'matches': lambda x: 17.0 <= x <= 18.49
    },
    {
        'min': 16.0, 'max': 16.9, 'name': "Недостаточность питания II ст.",
        'risk_level': "Высокий риск",
        'description': (
            "У вас наблюдается высокий риск заболеваний, связанных с недостаточным питанием, - "
            "белковая, белково-энергетическая недостаточность (истощение, кахексия), "
            "вследствие снижения резистентности организма к инфекционных и неинфекционным "
            "факторам высокая вероятность инфекционных заболеваний, болезней органов пищеварения"
        ),
        'matches': lambda x: 16.0 <= x <= 16.9
    },
    {
        'min': 0.0, 'max': 15.9, 'name': "Недостаточность питания III ст.",
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

def get_bmi_categories():
    """Возвращает конфигурацию категорий ИМТ (для совместимости с тестами)"""
    return BMI_CATEGORIES

# Словари для преобразования значений
BMI_SCORE_MAP = {
    "Нормальный ИМТ": 1.0,
    "Избыточная масса тела": 0.0,
    "Ожирение I ст.": 0.0,
    "Ожирение II ст.": 0.0,
    "Ожирение III ст.": 0.0
}

BP_STATUS_DESCRIPTIONS = {
    'normal': "У Вас нормальное артериальное давление",
    'elevated': "У Вас нормальное повышенное АД",
    'high': "У Вас высокое артериальное давление, необходима консультация специалиста (терапевта, кардиолога)",
    'unknown': (
        "Если Вам неизвестны значения Вашего артериального давления, то необходимо провести измерение. "
        "При значениях систолического давления выше 140 мм рт.ст и диастолического выше 90 мм рт.ст "
        "можно говорить о повышенном артериальном давлении. Необходима консультация специалиста "
        "(кардиолога, терапевта)"
    )
}


def calculate_user_rating(user_profile):
    """Основная функция расчета рейтинга пользователя"""
    result = initialize_base_result()
    responses = get_user_responses(user_profile)

    if not responses.exists():
        return result

    bmi_data = calculate_bmi_data(user_profile)
    processed_data = process_responses(responses, bmi_data, user_profile)

    category_averages = calculate_category_averages(processed_data['category_values'])
    total_score = calculate_total_score(category_averages)

    update_result(user_profile, result, bmi_data, category_averages, total_score, processed_data)
    return result


def initialize_base_result():
    """Инициализирует базовую структуру результата"""
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
    """Получает ответы пользователя с префетчингом"""
    return UserResponse.objects.filter(
        user_profile=user_profile
    ).prefetch_related(
        Prefetch('selected_answers', queryset=Answer.objects.only('value')),
        Prefetch('question', queryset=Question.objects.only('description'))
    )


def calculate_bmi_data(user_profile):
    """Рассчитывает данные ИМТ на основе профиля пользователя"""
    bmi_data = {
        'value': None,
        'category': 'Не рассчитан',
        'risk_level': 'Не определен',
        'risk_description': 'Данные для расчета отсутствуют'
    }

    if not (user_profile.height and user_profile.weight):
        return bmi_data

    try:
        if user_profile.height <= 0 or user_profile.weight <= 0:
            return bmi_data

        height_m = user_profile.height / 100
        bmi_value = user_profile.weight / (height_m ** 2)
        bmi_data['value'] = round(bmi_value, 1)

        for category in BMI_CATEGORIES:
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


def process_responses(responses, bmi_data, user_profile):
    """Обрабатывает все ответы пользователя и возвращает структурированные данные"""
    # Инициализация структур данных
    data = {
        'category_values': {key: [] for key in QUESTION_CATEGORIES},

        # Данные об имеющихся неинфекционных заболеваниях
        'diseases': [],

        # Антропометрические измерения
        'waist_hip_data': {'waist': None, 'hip': None},

        # Медицинские показатели
        'bp_data': {'systolic': None, 'diastolic': None, 'unknown': False},
        'cholesterol_data': {'value': None, 'unknown': False},
        'glucose_data': {'value': None, 'unknown': False},

        # Данные о курении
        'smoking_data': {'cigarettes': 0, 'years': 0},

        # Категория "Образ жизни"
        'physical_activity_values': [],
        'sleep_values': [],
        'digital_hygiene_values': [],
        'has_vacation_answers': False,
        'alcohol_alert': False,
        'smoking_alert': False,

        # Категория "Самооценка труда"
        'workplace_values': [],
        'physical_load_values': [],
        'work_pace_values': [],
        'emotional_load_values': [],
        'fatigue_values': [],
        'schedule_values': [],
        'digital_work_values': [],
        'critical_values': [],
        'extra_effort_values': [],
        'breaks_values': [],
        'lunch_break_values': [],
        'remote_work_values': [],

        # Категория "Питание"
        'meal_values': [],
        'interval_values': [],
        'breakfast_values': [],
        'density_values': [],
        'evening_meal_values': [],
        'fat_values': [],
        'hunger_values': [],
        'emotional_eating_values': [],
        'food_reward_values': [],

        # Категория "Пищевое поведение"
        'snack_values': [],
        'fast_food_values': [],
        'soda_values': [],
        'sausage_values': [],
        'smoked_values': [],
        'fat_product_values': [],
        'sauce_values': [],
        'fried_potato_values': [],
        'salted_values': [],
        'high_fat_dairy_values': [],
        'baking_values': [],
        'has_fruits_veggies_answer': False,
        'grain_values': [],
        'legume_values': [],
        'lean_meat_values': [],
        'seafood_values': [],
        'dairy_values': [],
        'has_oil_answer': False,
        'liquid_values': [],
        'salt_addition_values': [],
        'special_food_values': [],
        'supplements_values': [],

        # Флаги и агрегированные данные (будут заполнены в post_process)
        'has_low_activity': False,
        'has_sleep_issues': False,
        'has_digital_issues': False,
        'has_workplace_issues': False,
        'has_physical_load_issues': False,
        'has_work_pace_issues': False,
        'has_emotional_load_issues': False,
        'has_fatigue_issues': False,
        'has_schedule_issues': False,
        'has_digital_work_issues': False,
        'critical_data': {},
        'extra_effort_data': {},
        'has_breaks_issues': False,
        'has_lunch_issues': False,
        'remote_work_data': {},
        'meal_data': {},
        'interval_data': {},
        'breakfast_data': {},
        'density_data': {},
        'has_evening_meal_issues': False,
        'has_fat_issues': False,
        'has_hunger_issues': False,
        'emotional_eating_data': {},
        'has_food_reward_issues': False,
        'has_snack_issues': False,
        'fast_food_data': {},
        'has_soda_issues': False,
        'has_sosage_issues': False,
        'has_smoked_issues': False,
        'has_fat_products_issues': False,
        'has_sauce_issues': False,
        'has_fried_potato_issues': False,
        'has_salted_issues': False,
        'has_high_fat_dairy_issues': False,
        'has_baking_issues': False,
        'has_grain_issues': False,
        'has_legume_issues': False,
        'has_lean_meat_issues': False,
        'has_seafood_issues': False,
        'dairy_data': {},
        'has_liquid_issues': False,
        'has_salt_addition_issues': False,
        'has_special_foof_issues': False,
        'has_supplements_issues': False,
    }

    # Обработка каждого ответа
    for response in responses:
        process_single_response(response, data, user_profile)

    # Пост-обработка данных
    post_process_data(data, bmi_data, user_profile)

    return data


def process_single_response(response, data, user_profile):
    """Обрабатывает один ответ пользователя"""
    category = get_response_category(response)

    # Для числовых вопросов
    if response.question.is_numeric_input:
        values = [response.numeric_answer] if response.numeric_answer is not None else []
    else:
        values = [a.value for a in response.selected_answers.all() if a.value is not None]

    # Обработка специальных вопросов
    if handle_special_questions(response, values, data, user_profile):
        return

    # Обработка категории lifestyle (включая курение)
    if category == 'lifestyle':
        handle_lifestyle_response(response, values, data)
    elif category:
        data['category_values'][category].extend(values)


def get_response_category(response):
    """Определяет категорию для ответа на вопрос"""
    for key, params in QUESTION_CATEGORIES.items():
        if response.question.description in params['descriptions']:
            return key
    return None


def handle_special_questions(response, values, data, user_profile):
    """Обрабатывает специальные вопросы (талия, бедра, давление и т.д.)"""
    desc = response.question.description

    if desc == "ОКРУЖНОСТЬ (ТАЛИИ)":
        handle_waist_measurement(response, data, user_profile)
        return True

    elif desc == "ОКРУЖНОСТЬ (БЕДЕР)":
        handle_hip_measurement(response, data)
        return True

    elif desc == "ОБЩИЙ ХОЛЕСТЕРИН":
        handle_cholesterol(response, data)
        return True

    elif desc == "УРОВЕНЬ ГЛЮКОЗЫ":
        handle_glucose(response, data)
        return True

    elif desc == "Имеющиеся заболевания":
        handle_diseases(response, data)
        return True

    elif desc == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ":
        handle_blood_pressure(response, data)
        return True

    # Категория "Образ жизни"
    elif desc == "ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ":
        data['physical_activity_values'].extend(values)
        return True
    elif desc == "СОН":
        data['sleep_values'].extend(values)
        return True
    elif desc == "ЦИФРОВАЯ ГИГИЕНА":
        data['digital_hygiene_values'].extend(values)
        return True
    elif desc == "ОТПУСК":
        data['has_vacation_answers'] = True
        return True
    elif desc == "АЛКОГОЛЬ":
        data['alcohol_alert'] = True
        return True

    # Категория "Самооценка труда"
    elif desc == "РАБОЧЕЕ МЕСТО":
        data['workplace_values'].extend(values)
        return True
    elif desc == "ФИЗИЧЕСКИЕ НАГРУЗКИ":
        data['physical_load_values'].extend(values)
        return True
    elif desc == "ТЕМП РАБОТЫ":
        data['work_pace_values'].extend(values)
        return True
    elif desc == "ЭМОЦИОНАЛЬНАЯ НАГРУЗКА":
        data['emotional_load_values'].extend(values)
        return True
    elif desc == "УТОМЛЯЕМОСТЬ":
        data['fatigue_values'].extend(values)
        return True
    elif desc == "ГРАФИК РАБОТЫ":
        data['schedule_values'].extend(values)
        return True
    elif desc == "ТРУД С ЦИФРОВЫМИ УСТРОЙСТВАМИ":
        data['digital_work_values'].extend(values)
        return True
    elif desc == "КРИТИЧЕСКИЕ СИТУАЦИИ":
        data['critical_values'].extend(values)
        return True
    elif desc == "ЭКСТРА УСИЛИЯ":
        data['extra_effort_values'].extend(values)
        return True
    elif desc == "РЕГЛАМЕНТИРОВАННЫЕ ПЕРЕРЫВЫ":
        data['breaks_values'].extend(values)
        return True
    elif desc == "ОБЕДЕННЫЙ ПЕРЕРЫВ":
        data['lunch_break_values'].extend(values)
        return True
    elif desc == "РАБОТА НА ДОМУ":
        data['remote_work_values'].extend(values)
        return True

    # Категория "Питание"
    elif desc == "ПРИЕМЫ ПИЩИ":
        data['meal_values'].extend(values)
        return True
    elif desc == "ВРЕМЯ ПЕРЕРЫВОВ МЕЖДУ ЕДОЙ":
        data['interval_values'].extend(values)
        return True
    elif desc == "ЗАВТРАК":
        data['breakfast_values'].extend(values)
        return True
    elif desc == "НАИБОЛЕЕ ПЛОТНЫЙ ПРИЕМ ПИЩИ":
        data['density_values'].extend(values)
        return True
    elif desc == "ЕДА ДО СНА":
        data['evening_meal_values'].extend(values)
        return True
    elif desc == "ВИД ЖИРОВ":
        data['fat_values'].extend(values)
        return True
    elif desc == "ГОЛОД":
        data['hunger_values'].extend(values)
        return True
    elif desc == "ЭМОЦИОНАЛЬНЫЕ ПЕРЕКУСЫ":
        data['emotional_eating_values'].extend(values)
        return True
    elif desc == "ПООЩРЕНИЕ ИЛИ НАКАЗАНИЕ ЕДОЙ":
        data['food_reward_values'].extend(values)
        return True

    # Категория "Пищевое поведение"
    elif desc == "СНЕКИ":
        data['snack_values'].extend(values)
        return True
    elif desc == "ФАСТ-ФУД":
        data['fast_food_values'].extend(values)
        return True
    elif desc == "СЛАДКАЯ ГАЗИРОВКА":
        data['soda_values'].extend(values)
        return True
    elif desc == "КОЛБАСНЫЕ ИЗДЕЛИЯ":
        data['sausage_values'].extend(values)
        return True
    elif desc == "КОПЧЕНЫЕ ПРОДУКТЫ":
        data['smoked_values'].extend(values)
        return True
    elif desc == "ПИЩЕВЫЕ ЖИРЫ":
        data['fat_product_values'].extend(values)
        return True
    elif desc == "СОУСЫ":
        data['sauce_values'].extend(values)
        return True
    elif desc == "ЖАРЕННЫЙ КАРТОФЕЛЬ":
        data['fried_potato_values'].extend(values)
        return True
    elif desc == "СОЛЕНЫЕ И КОНСЕРВИРОВАННЫЕ ПРОДУКТЫ":
        data['salted_values'].extend(values)
        return True
    elif desc == "МОЛОЧНЫЕ ПРОДУКТЫ С ВЫСОКОЙ ЖИРНОСТЬЮ":
        data['high_fat_dairy_values'].extend(values)
        return True
    elif desc == "ВЫПЕЧКА":
        data['baking_values'].extend(values)
        return True
    elif desc == "КОЛИЧЕСТВО ФРУКТОВ И ОВОЩЕЙ":
        data['has_fruits_veggies_answer'] = True
        return True
    elif desc == "ЗЛАКОВЫЕ ПРОДУКТЫ":
        data['grain_values'].extend(values)
        return True
    elif desc == "БОБОВЫЕ":
        data['legume_values'].extend(values)
        return True
    elif desc == "НЕЖИРНОЕ МЯСО":
        data['lean_meat_values'].extend(values)
        return True
    elif desc == "РЫБА И МОРЕПРОДУКТЫ":
        data['seafood_values'].extend(values)
        return True
    elif desc == "МОЛОКО И КИСЛОМОЛОЧКА":
        data['dairy_values'].extend(values)
        return True
    elif desc == "РАСТИТЕЛЬНЫЕ МАСЛА":
        data['has_oil_answer'] = True
        return True
    elif desc == "ЖИДКОСТЬ В ДЕНЬ":
        data['liquid_values'].extend(values)
        return True
    elif desc == "ДОСАЛИВАНИЕ":
        data['salt_addition_values'].extend(values)
        return True
    elif desc == "СПЕЦИАЛЬНАЯ ПИЩЕВАЯ ПРОДУКЦИЯ":
        data['special_food_values'].extend(values)
        return True
    elif desc == "БАДЫ":
        data['supplements_values'].extend(values)
        return True

    return False


def handle_waist_measurement(response, data, user_profile):
    """Обрабатывает измерение окружности талии"""
    if response.numeric_answer is None:
        return

    waist_value = response.numeric_answer
    if 50 <= waist_value <= 200:  # Валидация
        # Расчет балла за талию
        if user_profile.gender == 'M':
            waist_score = 1.0 if waist_value <= 94 else 0.0
        else:
            waist_score = 1.0 if waist_value <= 80 else 0.0

        data['category_values']['medico_biological'].append(waist_score)
        data['waist_hip_data']['waist'] = waist_value


def handle_hip_measurement(response, data):
    """Обрабатывает измерение окружности бедер

    оценка дается в post_process_data так, как там нам нужно знать значение waist
    """
    if response.numeric_answer is None:
        return

    hip_value = response.numeric_answer
    if 50 <= hip_value <= 200:  # Валидация
        data['waist_hip_data']['hip'] = hip_value


def handle_cholesterol(response, data):
    """Обрабатывает ответ на вопрос о холестерине"""
    if response.numeric_answer is not None:
        try:
            value = float(response.numeric_answer)
            if value == 0.0:
                data['cholesterol_data'].update({'unknown': True, 'value': None})
            else:
                data['cholesterol_data'].update({'unknown': False, 'value': value})

            # Добавление балла в категорию
            cholesterol_score = 1.0 if 0 < value <= 5.5 else 0.0
            data['category_values']['medico_biological'].append(cholesterol_score)
        except (ValueError, TypeError):
            data['cholesterol_data']['unknown'] = True
    else:
        data['cholesterol_data']['unknown'] = True


def handle_glucose(response, data):
    """Обрабатывает ответ на вопрос об уровне глюкозы

    балл добавляется в post_process_data
    """
    if response.numeric_answer is not None:
        try:
            value = float(response.numeric_answer)
            if value == 0.0:
                data['glucose_data'].update({'unknown': True, 'value': None})
            else:
                data['glucose_data'].update({'value': value, 'unknown': False})
        except (ValueError, TypeError):
            data['glucose_data']['unknown'] = True
    else:
        data['glucose_data']['unknown'] = True


def handle_diseases(response, data):
    """Обрабатывает ответ об имеющихся неинфекционных заболеваниях"""
    data['diseases'].extend([a.text for a in response.selected_answers.all()])
    if response.free_text_answer:
        data['diseases'].append(response.free_text_answer)


def handle_blood_pressure(response, data):
    """Обрабатывает ответ об артериальном давлении"""
    if not response.free_text_answer:
        data['bp_data']['unknown'] = True
        return

    if '/' in response.free_text_answer:
        try:
            systolic, diastolic = map(int, response.free_text_answer.split('/'))
            data['bp_data'].update({
                'systolic': systolic,
                'diastolic': diastolic,
                'unknown': False
            })
        except (ValueError, TypeError):
            data['bp_data']['unknown'] = True
    else:
        data['bp_data']['unknown'] = True


def handle_lifestyle_response(response, values, data):
    """Обрабатывает ответы категории lifestyle"""
    desc = response.question.description

    if desc == "Курение (сигарет в день)":
        # Для числовых вопросов values содержит список с одним значением
        value = values[0] if values else 0
        data['smoking_data']['cigarettes'] = value
        data['smoking_alert'] = True
    elif desc == "Курение (лет стажа)":
        value = values[0] if values else 0
        data['smoking_data']['years'] = value
        data['smoking_alert'] = True
    else:
        data['category_values']['lifestyle'].extend(values)


def post_process_data(data, bmi_data, user_profile):
    """Выполняет пост-обработку данных после обработки всех ответов"""

    # Расчет индекса курения
    cigarettes = data['smoking_data'].get('cigarettes', 0)
    years = data['smoking_data'].get('years', 0)

    if cigarettes > 0 and years > 0:
        smoking_index = (cigarettes * years) / 20
        data['category_values']['lifestyle'].append(min(smoking_index, 1.0))

    # Добавление балла ИМТ
    bmi_score = BMI_SCORE_MAP.get(bmi_data.get('category', ''), 0.0)
    data['category_values']['medico_biological'].append(bmi_score)

    # Расчет показателя талия/бедро
    waist = data['waist_hip_data']['waist']
    hip = data['waist_hip_data']['hip']
    if waist is not None and hip is not None and hip > 0:
        ratio = waist / hip
        if user_profile.gender == 'M':
            ratio_score = 1.0 if ratio < 0.9 else 0.0
        else:
            ratio_score = 1.0 if ratio < 0.85 else 0.0
        data['category_values']['medico_biological'].append(ratio_score)

    # Добавление балла артериального давления
    bp_status = get_bp_status(data['bp_data'])
    bp_score = 1.0 if bp_status == 'normal' else 0.0
    data['category_values']['medico_biological'].append(bp_score)

    # Добавление балла глюкозы
    if not data['glucose_data']['unknown'] and data['glucose_data']['value'] is not None:
        value = data['glucose_data']['value']
        if value > 6.1:
            data['category_values']['medico_biological'].append(0.0)
        elif value > 5.6:
            data['category_values']['medico_biological'].append(0.0)
        else:
            data['category_values']['medico_biological'].append(1.0)
    else:
        data['category_values']['medico_biological'].append(0.0)

    # Анализ двигательной активности
    data['has_low_activity'] = any(v in (0, 0.5) for v in data['physical_activity_values'])

    # Анализ сна
    data['has_sleep_issues'] = any(v in (0, 0.5) for v in data['sleep_values'])

    # Анализ цифровой гигиены
    data['has_digital_issues'] = any(v in (0, 0.5) for v in data['digital_hygiene_values'])

    # Анализ условий труда
    data['has_workplace_issues'] = any(v in (0, 0.5) for v in data['workplace_values'])
    data['has_physical_load_issues'] = any(v in (0, 0.5) for v in data['physical_load_values'])
    data['has_work_pace_issues'] = any(v in (0, 0.5) for v in data['work_pace_values'])
    data['has_emotional_load_issues'] = any(v in (0, 0.5) for v in data['emotional_load_values'])
    data['has_fatigue_issues'] = any(v in (0, 0.5) for v in data['fatigue_values'])
    data['has_schedule_issues'] = any(v in (0, 0.5) for v in data['schedule_values'])
    data['has_digital_work_issues'] = any(v in (0, 0.5) for v in data['digital_work_values'])

    # Анализ критических ситуаций
    data['critical_data'] = {
        'has_critical_0': any(v == 0 for v in data['critical_values']),
        'has_critical_05': any(v == 0.5 for v in data['critical_values']),
        'has_critical_079': any(v == 0.79 for v in data['critical_values'])
    }

    # Анализ экстра усилий
    data['extra_effort_data'] = {
        'has_extra_05': any(v == 0.5 for v in data['extra_effort_values']),
        'has_extra_0': any(v == 0 for v in data['extra_effort_values'])
    }

    # Анализ перерывов
    data['has_breaks_issues'] = any(v in {0, 0.5, 0.79} for v in data['breaks_values'])
    data['has_lunch_issues'] = any(v in {0, 0.5} for v in data['lunch_break_values'])

    # Анализ удаленной работы
    data['remote_work_data'] = {
        'has_remote_05': any(v == 0.5 for v in data['remote_work_values']),
        'has_remote_0': any(v == 0 for v in data['remote_work_values'])
    }

    # Анализ питания
    data['meal_data'] = {
        'has_meal_05': any(v == 0.5 for v in data['meal_values']),
        'has_meal_0': any(v == 0 for v in data['meal_values'])
    }
    data['interval_data'] = {
        'has_interval_05': any(v == 0.5 for v in data['interval_values']),
        'has_interval_0': any(v == 0 for v in data['interval_values'])
    }
    data['breakfast_data'] = {
        'has_breakfast_0': any(v == 0 for v in data['breakfast_values']),
        'has_breakfast_05': any(v == 0.5 for v in data['breakfast_values']),
        'has_breakfast_079': any(v == 0.79 for v in data['breakfast_values'])
    }
    data['density_data'] = {
        'has_density_05': any(v == 0.5 for v in data['density_values']),
        'has_density_0': any(v == 0 for v in data['density_values'])
    }
    data['has_evening_meal_issues'] = any(v in {0, 0.5} for v in data['evening_meal_values'])
    data['has_fat_issues'] = any(v in {0, 0.5} for v in data['fat_values'])
    data['has_hunger_issues'] = any(v in {0, 0.5, 0.79} for v in data['hunger_values'])

    # Анализ эмоционального питания
    has_emotional_eating_0 = any(v == 0 for v in data['emotional_eating_values'])
    has_emotional_eating_05 = any(v == 0.5 for v in data['emotional_eating_values']) and not has_emotional_eating_0
    has_emotional_eating_079 = any(v == 0.79 for v in data['emotional_eating_values']) and not (
            has_emotional_eating_0 or has_emotional_eating_05)
    all_healthy = all(v == 1 for v in data['emotional_eating_values'])
    data['emotional_eating_data'] = {
        'has_emotional_eating_0': has_emotional_eating_0,
        'has_emotional_eating_05': has_emotional_eating_05,
        'has_emotional_eating_079': has_emotional_eating_079,
        'all_healthy': all_healthy
    }

    # Анализ пищевых привычек
    data['has_food_reward_issues'] = any(v in {0, 0.5} for v in data['food_reward_values'])
    data['has_snack_issues'] = any(v in {0, 0.5, 0.79} for v in data['snack_values'])

    # Анализ фаст-фуда
    data['fast_food_data'] = {
        'has_fast_food_0': any(v == 0 for v in data['fast_food_values']),
        'has_fast_food_05': any(v == 0.5 for v in data['fast_food_values']),
        'has_fast_food_079': any(v == 0.79 for v in data['fast_food_values'])
    }

    # Анализ напитков и продуктов
    data['has_soda_issues'] = any(v in {0, 0.5, 0.79} for v in data['soda_values'])
    data['has_sosage_issues'] = any(v in {0, 0.5} for v in data['sausage_values'])
    data['has_smoked_issues'] = any(v in {0, 0.5} for v in data['smoked_values'])
    data['has_fat_products_issues'] = any(v in {0, 0.5} for v in data['fat_product_values'])
    data['has_sauce_issues'] = any(v in {0, 0.5} for v in data['sauce_values'])
    data['has_fried_potato_issues'] = any(v in {0, 0.5} for v in data['fried_potato_values'])
    data['has_salted_issues'] = any(v in {0, 0.5} for v in data['salted_values'])
    data['has_high_fat_dairy_issues'] = any(v in {0, 0.5} for v in data['high_fat_dairy_values'])
    data['has_baking_issues'] = any(v in {0, 0.5} for v in data['baking_values'])

    # Анализ здорового питания
    data['has_grain_issues'] = any(v in {0, 0.5, 0.79} for v in data['grain_values'])
    data['has_legume_issues'] = any(v in {0, 0.5} for v in data['legume_values'])
    data['has_lean_meat_issues'] = any(v in {0, 0.5, 0.79} for v in data['lean_meat_values'])
    data['has_seafood_issues'] = any(v in {0, 0.5} for v in data['seafood_values'])

    # Анализ молочных продуктов
    data['dairy_data'] = {
        'has_dairy_low': any(v in (0.5, 0.79) for v in data['dairy_values']),
        'has_dairy_0': any(v == 0 for v in data['dairy_values'])
    }

    # Анализ жидкости и добавок
    data['has_liquid_issues'] = any(v in {0, 0.5} for v in data['liquid_values'])
    data['has_salt_addition_issues'] = any(v in {0, 0.5} for v in data['salt_addition_values'])
    data['has_special_foof_issues'] = any(v in {0, 0.5} for v in data['special_food_values'])
    data['has_supplements_issues'] = any(v in {0, 0.5} for v in data['supplements_values'])


def get_bp_status(bp_data):
    """Определяет статус артериального давления"""
    if bp_data['unknown'] or not bp_data['systolic'] or not bp_data['diastolic']:
        return 'unknown'

    systolic = bp_data['systolic']
    diastolic = bp_data['diastolic']

    if systolic >= 140 or diastolic >= 90:
        return 'high'
    elif systolic >= 130 or diastolic >= 85:
        return 'elevated'
    else:
        return 'normal'


def calculate_category_averages(category_values):
    """Рассчитывает средние значения по категориям"""
    averages = {}
    for category, values in category_values.items():
        # Для lifestyle применяем нормализацию
        if category == 'lifestyle':
            values = [min(val, 1.0) for val in values]

        avg = safe_average(values) if values else 0.0
        averages[f'{category}_avg'] = avg

    return averages


def safe_average(values):
    """Безопасно рассчитывает среднее значение только по ненулевым элементам"""
    non_zero_values = [val for val in values if val > 0]
    return round(sum(non_zero_values) / len(non_zero_values), 4) if non_zero_values else 0.0


def calculate_total_score(averages):
    """Рассчитывает общий балл"""
    total_values = [v for v in averages.values() if v > 0]
    return safe_average(total_values) if total_values else 0.0


def determine_rating(total_score):
    """Определяет рейтинг на основе общего балла"""
    if total_score <= 0.47:
        return "Неудовлетворительный"
    elif total_score <= 0.67:
        return "Удовлетворительный"
    elif total_score <= 0.89:
        return "Допустимый"
    return "Оптимальный"


def update_result(user_profile, result, bmi_data, category_averages, total_score, processed_data):
    """Обновляет итоговый результат расчетов"""
    # Обновление категорийных средних значений
    result.update(category_averages)

    # Обновление данных ИМТ
    result.update({
        'bmi': bmi_data.get('value', 'Нет данных'),
        'bmi_category': bmi_data.get('category', 'Не рассчитан'),
        'bmi_risk_level': bmi_data.get('risk_level', 'Не определен'),
        'bmi_risk_description': bmi_data.get('risk_description', 'Данные отсутствуют'),
        'existing_diseases': processed_data['diseases'] if processed_data['diseases'] else None
    })

    # Обновление данных талия/бедро
    waist = processed_data['waist_hip_data'].get('waist')
    hip = processed_data['waist_hip_data'].get('hip')
    ratio = waist / hip if waist and hip and hip > 0 else None

    waist_status_info = get_waist_status(user_profile, waist)
    ratio_status_info = get_ratio_status(user_profile, processed_data['waist_hip_data'])

    result.update({
        'waist': waist,
        'hip': hip,
        'waist_hip_ratio': ratio,
        'waist_status': waist_status_info.get('status') if waist_status_info else None,
        'waist_description': waist_status_info.get('description') if waist_status_info else None,
        'ratio_status': ratio_status_info.get('status') if ratio_status_info else None,
        'ratio_description': ratio_status_info.get('description') if ratio_status_info else None
    })

    # Обновление данных артериального давления
    result.update({
        'bp_data': processed_data['bp_data'],
        'bp_status': get_bp_status(processed_data['bp_data']),
        'bp_description': get_bp_description(processed_data['bp_data'])
    })

    # Обновление данных холестерина
    result.update({
        'cholesterol_value': processed_data['cholesterol_data'].get('value'),
        'cholesterol_status': 'high' if (processed_data['cholesterol_data'].get('value') or 0) > 5.5 else 'normal',
        'cholesterol_unknown': processed_data['cholesterol_data'].get('unknown', False)
    })

    # Обновление данных глюкозы
    result.update({
        'glucose_value': processed_data['glucose_data'].get('value'),
        'glucose_status': get_glucose_status(processed_data['glucose_data'].get('value')),
        'glucose_unknown': (
                processed_data['glucose_data']['unknown'] or
                processed_data['glucose_data'].get('value') is None or
                processed_data['glucose_data'].get('value') == 0
        )
    })

    smoking_index = None
    cigarettes = processed_data['smoking_data']['cigarettes']
    years = processed_data['smoking_data']['years']

    # Рассчитываем только если есть данные
    if cigarettes > 0 and years > 0:
        smoking_index = (cigarettes * years) / 20

    # Обновление данных образа жизни
    result.update({
        'physical_activity_alert': processed_data['has_low_activity'],
        'sleep_alert': processed_data['has_sleep_issues'],
        'digital_hygiene_alert': processed_data['has_digital_issues'],
        'vacation_alert': processed_data['has_vacation_answers'],
        'alcohol_alert': processed_data['alcohol_alert'],
        'smoking_index': smoking_index,
        'smoking_alert': processed_data['smoking_alert']
    })

    # Обновление данных самооценки труда
    result.update({
        'has_workplace_issues': processed_data['has_workplace_issues'],
        'has_physical_load_issues': processed_data['has_physical_load_issues'],
        'has_work_pace_issues': processed_data['has_work_pace_issues'],
        'has_emotional_load_issues': processed_data['has_emotional_load_issues'],
        'has_fatigue_issues': processed_data['has_fatigue_issues'],
        'has_schedule_issues': processed_data['has_schedule_issues'],
        'has_digital_work_issues': processed_data['has_digital_work_issues'],
        'critical_data': processed_data['critical_data'],
        'extra_effort_data': processed_data['extra_effort_data'],
        'has_breaks_issues': processed_data['has_breaks_issues'],
        'has_lunch_issues': processed_data['has_lunch_issues'],
        'remote_work_data': processed_data['remote_work_data']
    })

    # Обновление данных питания
    result.update({
        'meal_data': processed_data['meal_data'],
        'interval_data': processed_data['interval_data'],
        'breakfast_data': processed_data['breakfast_data'],
        'density_data': processed_data['density_data'],
        'has_evening_meal_issues': processed_data['has_evening_meal_issues'],
        'has_fat_issues': processed_data['has_fat_issues'],
        'has_hunger_issues': processed_data['has_hunger_issues'],
        'emotional_eating_data': processed_data['emotional_eating_data'],
        'has_food_reward_issues': processed_data['has_food_reward_issues']
    })

    # Обновление данных пищевого поведения
    result.update({
        'has_snack_issues': processed_data['has_snack_issues'],
        'fast_food_data': processed_data['fast_food_data'],
        'has_soda_issues': processed_data['has_soda_issues'],
        'has_sosage_issues': processed_data['has_sosage_issues'],
        'has_smoked_issues': processed_data['has_smoked_issues'],
        'has_fat_products_issues': processed_data['has_fat_products_issues'],
        'has_sauce_issues': processed_data['has_sauce_issues'],
        'has_fried_potato_issues': processed_data['has_fried_potato_issues'],
        'has_salted_issues': processed_data['has_salted_issues'],
        'has_high_fat_dairy_issues': processed_data['has_high_fat_dairy_issues'],
        'has_baking_issues': processed_data['has_baking_issues'],
        'has_fruits_veggies_answer': processed_data['has_fruits_veggies_answer'],
        'has_grain_issues': processed_data['has_grain_issues'],
        'has_legume_issues': processed_data['has_legume_issues'],
        'has_lean_meat_issues': processed_data['has_lean_meat_issues'],
        'has_seafood_issues': processed_data['has_seafood_issues'],
        'dairy_data': processed_data['dairy_data'],
        'has_oil_answer': processed_data['has_oil_answer'],
        'has_liquid_issues': processed_data['has_liquid_issues'],
        'has_salt_addition_issues': processed_data['has_salt_addition_issues'],
        'has_special_foof_issues': processed_data['has_special_foof_issues'],
        'has_supplements_issues': processed_data['has_supplements_issues']
    })

    # Общие показатели
    result['total_score'] = round(total_score, 2)
    result['rating'] = determine_rating(total_score)

    # Округление всех числовых значений
    for key in result:
        if isinstance(result[key], float):
            result[key] = round(result[key], 2)

    return result


def get_waist_status(profile, waist):
    """Определяет статус окружности талии"""
    try:
        waist = float(waist)
    except (TypeError, ValueError):
        return None

    if not waist or not profile.gender:
        return None

    gender = profile.gender
    status = 'Норма'
    description = 'Риск сопутствующих заболеваний снижен'

    if gender == 'M':
        if waist >= 102:
            status = 'Высокое значение'
            description = (
                "У вас наблюдается высокий риск развития метаболических нарушений, "
                "ассоциированных с избыточной массой тела и ожирением, - сахарного диабета "
                "2-ого типа и сердечно-сосудистых заболеваний"
            )
        elif waist >= 94:
            status = 'Повышенное значение'
            description = (
                "У вас повышен риск развития метаболических нарушений, "
                "ассоциированных с избыточной массой тела и ожирением, - сахарного диабета "
                "2-ого типа и сердечно-сосудистых заболеваний"
            )
    else:
        if waist >= 88:
            status = 'Высокое значение'
            description = (
                "У вас наблюдается высокий риск развития метаболических нарушений, "
                "ассоциированных с избыточной массой тела и ожирением, - сахарного диабета "
                "2-ого типа и сердечно-сосудистых заболеваний"
            )
        elif waist >= 80:
            status = 'Повышенное значение'
            description = (
                "У вас повышен риск развития метаболических нарушений, "
                "ассоциированных с избыточной массой тела и ожирением, - сахарного диабета "
                "2-ого типа и сердечно-сосудистых заболеваний"
            )

    return {'status': status, 'description': description}


def get_ratio_status(profile, data):
    """Определяет статус соотношения талия/бедро"""
    try:
        waist = float(data.get('waist'))
        hip = float(data.get('hip'))
    except (TypeError, ValueError):
        return None

    if not data.get('waist') or not data.get('hip') or not profile.gender:
        return None

    ratio = data['waist'] / data['hip']
    gender = profile.gender
    status = 'Норма'
    description = 'Риск сопутствующих заболеваний снижен'

    if (gender == 'M' and ratio >= 0.9) or (gender == 'F' and ratio >= 0.85):
        status = 'Повышенное значение'
        description = (
            "У вас наблюдается высокий риск развития метаболических нарушений, "
            "ассоциированных с избыточной массой тела и ожирением, - сахарного диабета "
            "2-ого типа и сердечно-сосудистых заболеваний"
        )

    return {'status': status, 'description': description}


def get_bp_description(bp_data):
    """Возвращает описание статуса артериального давления"""
    status = get_bp_status(bp_data)
    return BP_STATUS_DESCRIPTIONS.get(status, "Неизвестный статус")


def get_glucose_status(value):
    """Определяет статус уровня глюкозы"""
    if value is None or value == 0:
        return 'unknown'

    status = []
    if value > 5.6:
        status.append("превышение капиллярной нормы (>5.6 ммоль/л)")
    if value > 6.1:
        status.append("превышение венозной нормы (>6.1 ммоль/л)")

    return ", ".join(status) if status else "норма"


def save_survey_results(profile):
    """
    Сохраняет все ответы пользователя в формате JSON в SurveyResult
    """
    # Получаем все ответы пользователя с связанными данными
    user_responses = UserResponse.objects.filter(
        user_profile=profile
    ).select_related('question').prefetch_related('selected_answers')

    # Формируем структуру данных для JSON
    responses_data = {
        'profile_info': {
            'gender': profile.gender,
            'age': profile.age,
            'height': profile.height,
            'weight': profile.weight
        },
        'questions': []
    }

    for response in user_responses:
        question_data = {
            'question_id': response.question.id,
            'question_text': response.question.text,
            'question_order': response.question.order,
            'selected_answers': [],
            'free_text_answer': response.free_text_answer,
            'numeric_answer': response.numeric_answer
        }

        # Добавляем выбранные ответы
        for answer in response.selected_answers.all():
            question_data['selected_answers'].append({
                'answer_id': answer.id,
                'answer_text': answer.text,
                'value': answer.value,
                'recommendation': answer.recommendation
            })

        responses_data['questions'].append(question_data)

    # Рассчитываем рейтинг
    rating_data = calculate_user_rating(profile)

    # Сохраняем в SurveyResult
    with transaction.atomic():
        survey_result, created = SurveyResult.objects.update_or_create(
            user_profile=profile,
            defaults={
                'responses_data': responses_data,
                'calculated_rating': rating_data
            }
        )

    return survey_result
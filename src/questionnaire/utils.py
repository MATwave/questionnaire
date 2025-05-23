from django.db.models import Prefetch
from .models import Question, UserResponse, Answer

# TODO: сейчас это все рассчитывается по всем, хотя можно по пользователю, что снизит нагрузку

def get_question_categories():
    """Конфигурация категорий вопросов"""
    return {
        'stress': {
            'descriptions': ["СТРЕСС"],
            'label': 'СТРЕСС'
        },
        'nutrition': {
            'descriptions': ["ПИТАНИЕ",
                             "ПРИЕМЫ ПИЩИ",
                             "ВРЕМЯ ПЕРЕРЫВОВ МЕЖДУ ЕДОЙ",
                             "ЗАВТРАК",
                             "НАИБОЛЕЕ ПЛОТНЫЙ ПРИЕМ ПИЩИ",
                             "ЕДА ДО СНА",
                             "ВИД ЖИРОВ",
                             "ГОЛОД",
                             "ЭМОЦИОНАЛЬНЫЕ ПЕРЕКУСЫ",
                             "ПООЩРЕНИЕ ИЛИ НАКАЗАНИЕ ЕДОЙ"],
            'label': 'ПИТАНИЕ'
        },
        'eating_behavior': {
            'descriptions': ["ПИЩЕВОЕ ПОВЕДЕНИЕ",
                             "СНЕКИ",
                             "ФАСТ-ФУД",
                             "СЛАДКАЯ ГАЗИРОВКА",
                             "КОЛБАСНЫЕ ИЗДЕЛИЯ",
                             "КОПЧЕНЫЕ ПРОДУКТЫ",
                             "ПИЩЕВЫЕ ЖИРЫ",
                             "СОУСЫ",
                             "ЖАРЕННЫЙ КАРТОФЕЛЬ",
                             "СОЛЕНЫЕ И КОНСЕРВИРОВАННЫЕ ПРОДУКТЫ",
                             "МОЛОЧНЫЕ ПРОДУКТЫ С ВЫСОКОЙ ЖИРНОСТЬЮ",
                             "ВЫПЕЧКА",
                             "КОЛИЧЕСТВО ФРУКТОВ И ОВОЩЕЙ",
                             "ЗЛАКОВЫЕ ПРОДУКТЫ",
                             "БОБОВЫЕ",
                             "НЕЖИРНОЕ МЯСО",
                             "РЫБА И МОРЕПРОДУКТЫ",
                             "МОЛОКО И КИСЛОМОЛОЧКА",
                             "РАСТИТЕЛЬНЫЕ МАСЛА",
                             "ЖИДКОСТЬ В ДЕНЬ",
                             "ДОСАЛИВАНИЕ",
                             "СПЕЦИАЛЬНАЯ ПИЩЕВАЯ ПРОДУКЦИЯ",
                             "БАДЫ"],
            'label': 'Пищевое поведение'
        },
        'work_assessment': {
            'descriptions': ["САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА",
                             "РАБОЧЕЕ МЕСТО",
                             "ФИЗИЧЕСКИЕ НАГРУЗКИ",
                             "ТЕМП РАБОТЫ",
                             "ЭМОЦИОНАЛЬНАЯ НАГРУЗКА",
                             "УТОМЛЯЕМОСТЬ",
                             "ГРАФИК РАБОТЫ",
                             "ТРУД С ЦИФРОВЫМИ УСТРОЙСТВАМИ",
                             "КРИТИЧЕСКИЕ СИТУАЦИИ",
                             "ЭКСТРА УСИЛИЯ",
                             "РЕГЛАМЕНТИРОВАННЫЕ ПЕРЕРЫВЫ",
                             "ОБЕДЕННЫЙ ПЕРЕРЫВ",
                             "РАБОТА НА ДОМУ"],
            'label': 'Самооценка труда'
        },
        'lifestyle': {
            'descriptions': ["ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ",
                             "СОН",
                             "ЦИФРОВАЯ ГИГИЕНА",
                             "ОТПУСК",
                             "АЛКОГОЛЬ",
                "ОБРАЗ ЖИЗНИ И РЕЖИМ ДНЯ",
                "Курение (сигарет в день)",
                "Курение (лет стажа)"
            ],
            'label': 'Образ жизни и ФАиРД'
        },
            'medico_biological': {
            'descriptions': ["МЕДИКО-БИОЛОГИЧЕСКИЕ ФАКТОРЫ",
                             "Имеющиеся заболевания",
                             "ОКРУЖНОСТЬ (ТАЛИИ)",
                             "ОКРУЖНОСТЬ (БЕДЕР)",
                             "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ",
                             "ОБЩИЙ ХОЛЕСТЕРИН",
                             "УРОВЕНЬ ГЛЮКОЗЫ"],
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
    (category_values, smoking_data, diseases, waist_hip_data, bp_data, cholesterol_data,
     glucose_data, has_low_activity, has_sleep_issues, has_digital_issues,
     has_vacation_answers, alcohol_alert, smoking_alert, has_workplace_issues,
     has_physical_load_issues, has_work_pace_issues, has_emotional_load_issues,
     has_fatigue_issues, has_schedule_issues, has_digital_work_issues, critical_data,
     extra_effort_data, has_breaks_issues, has_lunch_issues, remote_work_data, meal_data, interval_data,
     breakfast_data, density_data, has_evening_meal_issues, has_fat_issues, has_hunger_issues,
     emotional_eating_data, has_food_reward_issues, has_snack_issues, fast_food_data, has_soda_issues,
     has_sosage_issues, has_smoked_issues, has_fat_products_issues, has_sauce_issues, has_fried_potato_issues,
     has_salted_issues, has_high_fat_dairy_issues, has_baking_issues, has_fruits_veggies_answer,
     has_grain_issues, has_legume_issues, has_lean_meat_issues, has_seafood_issues,
     dairy_data, has_oil_answer, has_liquid_issues, has_salt_addition_issues,
     has_special_foof_issues, has_supplements_issues)  = process_responses(responses, bmi_data, user_profile)
    # Расчет средних значений по категориям
    category_averages = calculate_category_averages(category_values)

    # Расчет общего балла
    total_score = calculate_total_score(category_averages)

    # Обновление результата
    update_result(
        user_profile,
        result,
        bmi_data,
        category_averages,
        total_score,
        smoking_data,
        diseases,
        waist_hip_data,
        bp_data,
        cholesterol_data,
        glucose_data,
        has_low_activity,
        has_sleep_issues,
        has_digital_issues,
        has_vacation_answers,
        alcohol_alert,
        smoking_alert,
        has_workplace_issues,
        has_physical_load_issues,
        has_work_pace_issues,
        has_emotional_load_issues,
        has_fatigue_issues,
        has_schedule_issues,
        has_digital_work_issues,
        critical_data,
        extra_effort_data,
        has_breaks_issues,
        has_lunch_issues,
        remote_work_data,
        meal_data,
        interval_data,
        breakfast_data,
        density_data,
        has_evening_meal_issues,
        has_fat_issues,
        has_hunger_issues,
        emotional_eating_data,
        has_food_reward_issues,
        has_snack_issues,
        fast_food_data,
        has_soda_issues,
        has_sosage_issues,
        has_smoked_issues,
        has_fat_products_issues,
        has_sauce_issues,
        has_fried_potato_issues,
        has_salted_issues,
        has_high_fat_dairy_issues,
        has_baking_issues,
        has_fruits_veggies_answer,
        has_grain_issues,
        has_legume_issues,
        has_lean_meat_issues,
        has_seafood_issues,
        dairy_data,
        has_oil_answer,
        has_liquid_issues,
        has_salt_addition_issues,
        has_special_foof_issues,
        has_supplements_issues
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


def get_bp_status(bp_data):
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


def get_bp_description(bp_data):
    status = get_bp_status(bp_data)

    descriptions = {
        'normal': "У Вас нормальное артериальное давление",
        'elevated': "У Вас нормальное повышенное АД",
        'high': "У Вас высокое артериальное давление, необходима консультация специалиста (терапевта, кардиолога)",
        'unknown': "Если Вам неизвестны значения Вашего артериального давления, то необходимо провести измерение. При значениях систолического давления выше 140 мм рт.ст и диастолического выше 90 мм рт.ст можно говорить о повышенном артериальном давлении. Необходима консультация специалиста (кардиолога, терапевта)"
    }
    return descriptions[status]


def get_glucose_status(value):
    """Определение статуса глюкозы"""
    if value is None or value == 0:
        return 'unknown'

    status = []
    if value > 5.6:
        status.append("превышение капиллярной нормы (>5.6 ммоль/л)")
    if value > 6.1:
        status.append("превышение венозной нормы (>6.1 ммоль/л)")

    return ", ".join(status) if status else "норма"


def process_responses(responses, bmi_data, user_profile):
    """Обработка ответов пользователя"""
    categories = get_question_categories()
    category_values = {key: [] for key in categories}
    smoking_data = {'cigarettes': 0, 'years': 0}
    diseases = []
    waist_hip_data = {'waist': None, 'hip': None}
    bp_data = {'systolic': None, 'diastolic': None, 'unknown': False}
    cholesterol_data = {'value': None, 'unknown': False}
    glucose_data = {'value': None, 'unknown': False}
    physical_activity_values = []
    sleep_values = []
    digital_hygiene_values = []
    has_vacation_answers = False
    alcohol_alert = False
    smoking_alert = False
    workplace_values = []
    physical_load_values = []
    work_pace_values = []
    emotional_load_values = []
    fatigue_values = []
    schedule_values = []
    digital_work_values = []
    critical_values = []
    extra_effort_values = []
    breaks_values = []
    lunch_break_values = []
    remote_work_values = []
    meal_values = []
    interval_values = []
    breakfast_values = []
    density_values = []
    evening_meal_values = []
    fat_values = []
    hunger_values = []
    emotional_eating_values = []
    food_reward_values = []
    snack_values = []
    fast_food_values = []
    soda_values = []
    sausage_values = []
    smoked_values = []
    fat_product_values = []
    sauce_values = []
    fried_potato_values = []
    salted_values = []
    high_fat_dairy_values = []
    baking_values = []
    has_fruits_veggies_answer = False
    grain_values = []
    legume_values = []
    lean_meat_values = []
    seafood_values = []
    dairy_values = []
    has_oil_answer = False
    liquid_values = []
    salt_addition_values = []
    special_food_values = []
    supplements_values = []

    # 1. Обработка обычных ответов
    for response in responses:
        category = get_response_category(response, categories)
        if not category:
            continue

        # Для числовых вопросов используем numeric_answer
        if response.question.is_numeric_input:
            values = [response.numeric_answer] if response.numeric_answer is not None else []
        else:
            values = get_answer_values(response)

        # Сбор данных для талии/бедер
        if response.question.description == "ОКРУЖНОСТЬ (ТАЛИИ)":
            waist_value = response.numeric_answer
            if waist_value is not None and 50 <= waist_value <= 200:  # Валидация
                # Балл за талию
                if user_profile.gender == 'M':
                    waist_score = 1.0 if waist_value <= 94 else (0.5 if waist_value <= 102 else 0.0)
                else:
                    waist_score = 1.0 if waist_value <= 80 else (0.5 if waist_value <= 88 else 0.0)
                category_values['medico_biological'].append(waist_score)
                waist_hip_data['waist'] = waist_value
        elif response.question.description == "ОКРУЖНОСТЬ (БЕДЕР)":
            hip_value = response.numeric_answer
            if hip_value is not None and 50 <= hip_value <= 200:  # Валидация
                waist_hip_data['hip'] = hip_value
        elif response.question.description == "ОБЩИЙ ХОЛЕСТЕРИН":
            if response.numeric_answer is not None:
                try:
                    value = float(response.numeric_answer)
                    cholesterol_data['value'] = value
                    cholesterol_data['unknown'] = False
                    # Непосредственно добавляем балл
                    cholesterol_score = 1.0 if value <= 5.5 else 0.0
                    category_values['medico_biological'].append(cholesterol_score)
                except:
                    cholesterol_data['unknown'] = True
            else:
                cholesterol_data['unknown'] = True
        elif response.question.description == "УРОВЕНЬ ГЛЮКОЗЫ":
            if response.numeric_answer is not None:
                try:
                    value = float(response.numeric_answer)
                    if value == 0.0:
                        glucose_data.update({'unknown': True, 'value': None})
                    else:
                        glucose_data.update({'value': value, 'unknown': False})
                except:
                    glucose_data['unknown'] = True
            else:
                glucose_data['unknown'] = True
        elif response.question.description == "Имеющиеся заболевания":
            diseases.extend([a.text for a in response.selected_answers.all()])
            if response.free_text_answer:
                diseases.append(response.free_text_answer)
        elif response.question.description == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ":
            if response.free_text_answer:
                if '/' in response.free_text_answer:
                    try:
                        systolic, diastolic = map(int, response.free_text_answer.split('/'))
                        bp_data.update({
                            'systolic': systolic,
                            'diastolic': diastolic,
                            'unknown': False
                        })
                    except:
                        bp_data['unknown'] = True
                else:
                    bp_data['unknown'] = True
        elif response.question.description == "ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ":
            physical_activity_values.extend(values)
        elif response.question.description == "СОН":
            sleep_values.extend(values)
        elif response.question.description == "ЦИФРОВАЯ ГИГИЕНА":
            digital_hygiene_values.extend(values)
        elif response.question.description == "ОТПУСК":
            has_vacation_answers = True
        elif response.question.description == "АЛКОГОЛЬ":
            alcohol_alert = True
        elif "Курение" in response.question.description:
            smoking_alert = True
        elif response.question.description == "РАБОЧЕЕ МЕСТО":
            workplace_values.extend(values)
        elif response.question.description == "ФИЗИЧЕСКИЕ НАГРУЗКИ":
            physical_load_values.extend(values)
        elif response.question.description == "ТЕМП РАБОТЫ":
            work_pace_values.extend(values)
        elif response.question.description == "ЭМОЦИОНАЛЬНАЯ НАГРУЗКА":
            emotional_load_values.extend(values)
        elif response.question.description == "УТОМЛЯЕМОСТЬ":
            fatigue_values.extend(values)
        elif response.question.description == "ГРАФИК РАБОТЫ":
            schedule_values.extend(values)
        elif response.question.description == "ТРУД С ЦИФРОВЫМИ УСТРОЙСТВАМИ":
            digital_work_values.extend(values)
        elif response.question.description == "КРИТИЧЕСКИЕ СИТУАЦИИ":
            critical_values.extend(values)
        elif response.question.description == "ЭКСТРА УСИЛИЯ":
            extra_effort_values.extend(values)
        elif response.question.description == "РЕГЛАМЕНТИРОВАННЫЕ ПЕРЕРЫВЫ":
            breaks_values.extend(values)
        elif response.question.description == "ОБЕДЕННЫЙ ПЕРЕРЫВ":
            lunch_break_values.extend(values)
        elif response.question.description == "РАБОТА НА ДОМУ":
            remote_work_values.extend(values)
        elif response.question.description == "ПРИЕМЫ ПИЩИ":
            meal_values.extend(values)
        elif response.question.description == "ВРЕМЯ ПЕРЕРЫВОВ МЕЖДУ ЕДОЙ":
            interval_values.extend(values)
        elif response.question.description == "ЗАВТРАК":
            breakfast_values.extend(values)
        elif response.question.description == "НАИБОЛЕЕ ПЛОТНЫЙ ПРИЕМ ПИЩИ":
            density_values.extend(values)
        elif response.question.description == "ЕДА ДО СНА":
            evening_meal_values.extend(values)
        elif response.question.description == "ВИД ЖИРОВ":
            fat_values.extend(values)
        elif response.question.description == "ГОЛОД":
            hunger_values.extend(values)
        elif response.question.description == "ЭМОЦИОНАЛЬНЫЕ ПЕРЕКУСЫ":
            emotional_eating_values.extend(values)
        elif response.question.description == "ПООЩРЕНИЕ ИЛИ НАКАЗАНИЕ ЕДОЙ":
            food_reward_values.extend(values)
        elif response.question.description == "СНЕКИ":
            snack_values.extend(values)
        elif response.question.description == "ФАСТ-ФУД":
            fast_food_values.extend(values)
        elif response.question.description == "СЛАДКАЯ ГАЗИРОВКА":
            soda_values.extend(values)
        elif response.question.description == "КОЛБАСНЫЕ ИЗДЕЛИЯ":
            sausage_values.extend(values)
        elif response.question.description == "КОПЧЕНЫЕ ПРОДУКТЫ":
            smoked_values.extend(values)
        elif response.question.description == "ПИЩЕВЫЕ ЖИРЫ":
            fat_product_values.extend(values)
        elif response.question.description == "СОУСЫ":
            sauce_values.extend(values)
        elif response.question.description == "ЖАРЕННЫЙ КАРТОФЕЛЬ":
            fried_potato_values.extend(values)
        elif response.question.description == "СОЛЕНЫЕ И КОНСЕРВИРОВАННЫЕ ПРОДУКТЫ":
            salted_values.extend(values)
        elif response.question.description == "МОЛОЧНЫЕ ПРОДУКТЫ С ВЫСОКОЙ ЖИРНОСТЬЮ":
            high_fat_dairy_values.extend(values)
        elif response.question.description == "ВЫПЕЧКА":
            baking_values.extend(values)
        elif response.question.description == "КОЛИЧЕСТВО ФРУКТОВ И ОВОЩЕЙ":
            has_fruits_veggies_answer = True
        elif response.question.description == "ЗЛАКОВЫЕ ПРОДУКТЫ":
            grain_values.extend(values)
        elif response.question.description == "БОБОВЫЕ":
            legume_values.extend(values)
        elif response.question.description == "НЕЖИРНОЕ МЯСО":
            lean_meat_values.extend(values)
        elif response.question.description == "РЫБА И МОРЕПРОДУКТЫ":
            seafood_values.extend(values)
        elif response.question.description == "МОЛОКО И КИСЛОМОЛОЧКА":
            dairy_values.extend(values)
        elif response.question.description == "РАСТИТЕЛЬНЫЕ МАСЛА":
            has_oil_answer = True
        elif response.question.description == "ЖИДКОСТЬ В ДЕНЬ":
            liquid_values.extend(values)
        elif response.question.description == "ДОСАЛИВАНИЕ":
            salt_addition_values.extend(values)
        elif response.question.description == "СПЕЦИАЛЬНАЯ ПИЩЕВАЯ ПРОДУКЦИЯ":
            special_food_values.extend(values)
        elif response.question.description == "БАДЫ":
            supplements_values.extend(values)

        if category == 'lifestyle':
            handle_smoking_response(response, values, smoking_data, category_values)
        elif category == 'medico_biological':
            pass
        else:
            category_values[category].extend(values)

    # 2. Добавляем индекс курильщика
    if smoking_data['cigarettes'] > 0 and smoking_data['years'] > 0:
        smoking_index = (smoking_data['cigarettes'] * smoking_data['years']) / 20
        category_values['lifestyle'].append(min(smoking_index, 1.0))

    # 3. Добавляем ИМТ как отдельный показатель (исправленная версия)
    bmi_score_map = {
        "Нормальный ИМТ": 1.0,
        "Избыточная масса тела": 0.5,
        "Ожирение I ст.": 0.3,
        "Ожирение II ст.": 0.1,
        "Ожирение III ст.": 0.0
    }
    bmi_score = bmi_score_map.get(bmi_data.get('category', ''), 0.0)
    category_values['medico_biological'].append(bmi_score)

    # 4. Расчет показателей талии/бедер

    if waist_hip_data['waist'] is not None and waist_hip_data['hip'] is not None and waist_hip_data['hip'] > 0:
        ratio = waist_hip_data['waist'] / waist_hip_data['hip']

        if user_profile.gender == 'M':
            ratio_score = 1.0 if ratio < 0.9 else 0.0
        else:
            ratio_score = 1.0 if ratio < 0.85 else 0.0

        category_values['medico_biological'].append(ratio_score)

    # 5. Артериальное давление (остается без изменений)
    bp_status = get_bp_status(bp_data)
    bp_score = 1.0 if bp_status == 'normal' else (0.5 if bp_status == 'elevated' else 0.0)
    category_values['medico_biological'].append(bp_score)

    #6. халестерин. Балл добавляем выше при обработке

    #7. глюкоза
    if not glucose_data['unknown'] and glucose_data['value'] is not None:
        value = glucose_data['value']
        if value > 6.1:
            category_values['medico_biological'].append(0.0)
        elif value > 5.6:
            category_values['medico_biological'].append(0.5)
        else:
            category_values['medico_biological'].append(1.0)
    else:
        # Обработка неизвестного значения
        category_values['medico_biological'].append(0.0)

    # двигательная активность
    has_low_activity = any(v in (0, 0.5) for v in physical_activity_values)
    # сон
    has_sleep_issues = any(v in (0, 0.5) for v in sleep_values)
    # цифровая гигиена
    has_digital_issues = any(v in (0, 0.5) for v in digital_hygiene_values)
    # рабочее место
    has_workplace_issues = any(v in (0, 0.5) for v in workplace_values)
    # физические нагрузки
    has_physical_load_issues = any(v in (0, 0.5) for v in physical_load_values)
    # тем работы
    has_work_pace_issues = any(v in (0, 0.5) for v in work_pace_values)
    # эмоциональная нагрузка
    has_emotional_load_issues = any(v in (0, 0.5) for v in emotional_load_values)
    # утомнляемость
    has_fatigue_issues = any(v in (0, 0.5) for v in fatigue_values)
    # график работы
    has_schedule_issues = any(v in (0, 0.5) for v in schedule_values)
    # труд с цифровыми устройствами
    has_digital_work_issues = any(v in (0, 0.5) for v in digital_work_values)
    # критические ситуации
    critical_data = {
            'has_critical_0': any(v == 0 for v in critical_values),
            'has_critical_05': any(v == 0.5 for v in critical_values),
            'has_critical_079': any(v == 0.79 for v in critical_values)
        }
    # экстра усилия
    extra_effort_data = {
        'has_extra_05': any(v == 0.5 for v in extra_effort_values),
        'has_extra_0': any(v == 0 for v in extra_effort_values)
    }
    # регламентированные перерывы
    has_breaks_issues = any(v in {0, 0.5, 0.79} for v in breaks_values)
    # обеденные перерывы
    has_lunch_issues = any(v in {0, 0.5} for v in lunch_break_values)
    # работа на дом
    remote_work_data = {
            'has_remote_05': any(v == 0.5 for v in remote_work_values),
            'has_remote_0': any(v == 0 for v in remote_work_values)
        }
    # приемы пищи
    meal_data = {
            'has_meal_05': any(v == 0.5 for v in meal_values),
            'has_meal_0': any(v == 0 for v in meal_values)
        }
    # перерыв между едой
    interval_data = {
        'has_interval_05': any(v == 0.5 for v in interval_values),
        'has_interval_0': any(v == 0 for v in interval_values)
    }
    # завтрак
    breakfast_data = {
            'has_breakfast_0': any(v == 0 for v in breakfast_values),
            'has_breakfast_05': any(v == 0.5 for v in breakfast_values),
            'has_breakfast_079': any(v == 0.79 for v in breakfast_values)
        }
    # наиболее плотный прием пищи
    density_data = {
            'has_density_05': any(v == 0.5 for v in density_values),
            'has_density_0': any(v == 0 for v in density_values)
        }
    # еда до сна
    has_evening_meal_issues = any(v in {0, 0.5} for v in evening_meal_values)
    # виды жиров
    has_fat_issues = any(v in {0, 0.5} for v in fat_values)
    # голод
    has_hunger_issues = any(v in {0, 0.5, 0.79} for v in hunger_values)
    # эмоциональные перекусы
    has_emotional_eating_0 = any(v == 0 for v in emotional_eating_values)
    has_emotional_eating_05 = any(v == 0.5 for v in emotional_eating_values) and not has_emotional_eating_0
    has_emotional_eating_079 = any(v == 0.79 for v in emotional_eating_values) and not (
                has_emotional_eating_0 or has_emotional_eating_05)
    all_healthy = all(v == 1 for v in emotional_eating_values)
    emotional_eating_data = {
            'has_emotional_eating_0': has_emotional_eating_0,
            'has_emotional_eating_05': has_emotional_eating_05,
            'has_emotional_eating_079': has_emotional_eating_079,
            'all_healthy': all_healthy
        }
    # поощрение или наказание едой
    has_food_reward_issues = any(v in {0, 0.5, 0.79} for v in food_reward_values)
    # снеки
    has_snack_issues = any(v in {0, 0.5, 0.79} for v in snack_values)
    # фаст-фуд
    fast_food_data = {
            'has_fast_food_0': any(v == 0 for v in fast_food_values),
            'has_fast_food_05': any(v == 0.5 for v in fast_food_values),
            'has_fast_food_079': any(v == 0.79 for v in fast_food_values)
        }
    # сладкая газировка
    has_soda_issues = any(v in {0, 0.5, 0.79} for v in soda_values)
    # колбасные изделия
    has_sosage_issues = any(v in {0, 0.5} for v in sausage_values)
    # копченые продукты
    has_smoked_issues = any(v in {0, 0.5} for v in smoked_values)
    # пищевые жиры
    has_fat_products_issues = any(v in {0, 0.5} for v in fat_product_values)
    # соусы
    has_sauce_issues = any(v in {0, 0.5} for v in sauce_values)
    # жаренный картофель
    has_fried_potato_issues = any(v in {0, 0.5} for v in fried_potato_values)
    # соленые и консервированные продукты
    has_salted_issues = any(v in {0, 0.5} for v in salted_values)
    # молочные продукты с высоким содержанием жира
    has_high_fat_dairy_issues = any(v in {0, 0.5} for v in high_fat_dairy_values)
    # выпечка
    has_baking_issues = any(v in {0, 0.5} for v in baking_values)
    # злаковые
    has_grain_issues = any(v in {0, 0.5, 0.79} for v in grain_values)
    # бобовые
    has_legume_issues = any(v in {0, 0.5} for v in legume_values)
    # нежирное мясо
    has_lean_meat_issues = any(v in {0, 0.5, 0.79} for v in lean_meat_values)
    # рыба и морепродукты
    has_seafood_issues = any(v in {0, 0.5} for v in seafood_values)
    # молоко и кисломолочка
    dairy_data = {
        'has_dairy_low': any(v in (0.5, 0.79) for v in dairy_values),
        'has_dairy_0': any(v == 0 for v in dairy_values)
    }
    # жидкость в день
    has_liquid_issues = any(v in {0, 0.5} for v in liquid_values)
    # досаливание
    has_salt_addition_issues = any(v in {0, 0.5} for v in salt_addition_values)
    # специальная пищевая продукция
    has_special_foof_issues = any(v in {0, 0.5} for v in special_food_values)
    # бады
    has_supplements_issues = any(v in {0, 0.5} for v in supplements_values)

    return (category_values, smoking_data, diseases, waist_hip_data, bp_data, cholesterol_data,
            glucose_data, has_low_activity, has_sleep_issues, has_digital_issues, has_vacation_answers,
            alcohol_alert, smoking_alert, has_workplace_issues, has_physical_load_issues, has_work_pace_issues,
            has_emotional_load_issues, has_fatigue_issues, has_schedule_issues, has_digital_work_issues, critical_data,
            extra_effort_data, has_breaks_issues, has_lunch_issues, remote_work_data, meal_data, interval_data,
            breakfast_data, density_data, has_evening_meal_issues,has_fat_issues, has_hunger_issues,
            emotional_eating_data, has_food_reward_issues, has_snack_issues, fast_food_data, has_soda_issues,
            has_sosage_issues, has_smoked_issues, has_fat_products_issues,has_sauce_issues, has_fried_potato_issues,
            has_salted_issues, has_high_fat_dairy_issues, has_baking_issues, has_fruits_veggies_answer,
            has_grain_issues, has_legume_issues, has_lean_meat_issues, has_seafood_issues, dairy_data, has_oil_answer,
            has_liquid_issues, has_salt_addition_issues, has_special_foof_issues, has_supplements_issues)


def get_response_category(response, categories):
    """Определение категории для ответа"""
    for key, params in categories.items():
        if response.question.description in params['descriptions']:
            return key
    return None


def get_answer_values(response):
    """Получение значений ответов"""
    return [a.value for a in response.selected_answers.all() if a.value is not None]


def handle_smoking_response(response, values, smoking_data, category_values):
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


def get_waist_status(profile, waist):
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

def update_result(user_profile, result, bmi_data, category_averages, total_score, smoking_data, diseases,
                  waist_hip_data, bp_data, cholesterol_data, glucose_data, physical_activity_data, sleep_data,
                  has_digital_issues, has_vacation_answers, alcohol_alert, smoking_alert, has_workplace_issues,
                  has_physical_load_issues, has_work_pace_issues, has_emotional_load_issues, has_fatigue_issues,
                  has_schedule_issues, has_digital_work_issues, critical_data, extra_effort_data, has_breaks_issues,
                  has_lunch_issues, remote_work_data, meal_data, interval_data, breakfast_data, density_data,
                  has_evening_meal_issues,has_fat_issues, has_hunger_issues,emotional_eating_data,
                  has_food_reward_issues, has_snack_issues, fast_food_data, has_soda_issues, has_sosage_issues,
                  has_smoked_issues, has_fat_products_issues,has_sauce_issues, has_fried_potato_issues,
                  has_salted_issues, has_high_fat_dairy_issues, has_baking_issues, has_fruits_veggies_answer,
                  has_grain_issues, has_legume_issues, has_lean_meat_issues, has_seafood_issues, dairy_data,
                  has_oil_answer, has_liquid_issues, has_salt_addition_issues, has_special_foof_issues, has_supplements_issues):
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

    # Добавляем расчет соотношения талия/бедро
    waist = waist_hip_data.get('waist')
    hip = waist_hip_data.get('hip')
    ratio = None
    if waist and hip and hip > 0:
        ratio = waist / hip

    # Обновляем данные для талии
    waist_status_info = get_waist_status(user_profile, waist)
    ratio_status_info = get_ratio_status(user_profile, waist_hip_data)

    result.update({
        'waist': waist,
        'hip': hip,
        'waist_hip_ratio': ratio,
        'waist_status': waist_status_info.get('status') if waist_status_info else None,
        'waist_description': waist_status_info.get('description') if waist_status_info else None,
        'ratio_status': ratio_status_info.get('status') if ratio_status_info else None,
        'ratio_description': ratio_status_info.get('description') if ratio_status_info else None
    })

    result.update({
        'bp_data': bp_data,
        'bp_status': get_bp_status(bp_data),
        'bp_description': get_bp_description(bp_data)
    })

    result.update({
        'cholesterol_value': cholesterol_data.get('value'),
        'cholesterol_status': 'high' if (cholesterol_data.get('value') or 0) > 5.5 else 'normal',
        'cholesterol_unknown': cholesterol_data.get('unknown', False)
    })

    result.update({
        'glucose_value': glucose_data.get('value'),
        'glucose_status': get_glucose_status(glucose_data.get('value')),
        'glucose_unknown': glucose_data['unknown'] or glucose_data.get('value') is None or glucose_data.get('value') == 0
    })

    result.update({
        'physical_activity_alert': physical_activity_data,
    })

    result.update({
        'sleep_alert': sleep_data,
    })
    result.update({
        'digital_hygiene_alert': has_digital_issues
    })

    result.update({
        'vacation_alert': has_vacation_answers
    })

    result.update({
        'alcohol_alert':alcohol_alert
    })

    result.update({
        'smoking_index': (smoking_data['cigarettes'] * smoking_data['years']) / 20
        if smoking_data['cigarettes'] > 0 and smoking_data['years'] > 0
        else None,
        'smoking_alert': smoking_alert
    })

    result.update({
        'has_workplace_issues': has_workplace_issues
    })

    result.update({
        'has_physical_load_issues': has_physical_load_issues
    })

    result.update({
        'has_work_pace_issues': has_work_pace_issues
    })

    result.update({
        'has_emotional_load_issues': has_emotional_load_issues
    })

    result.update({
        'has_fatigue_issues': has_fatigue_issues
    })

    result.update({
        'has_schedule_issues': has_schedule_issues
    })

    result.update({
        'has_digital_work_issues': has_digital_work_issues
    })

    result.update({
        'critical_data': critical_data
    })

    result.update({
        'extra_effort_data': extra_effort_data
    })

    result.update({
        'has_breaks_issues': has_breaks_issues
    })

    result.update({
        'has_lunch_issues': has_lunch_issues
    })

    result.update({
        'remote_work_data': remote_work_data
    })

    result.update({
        'meal_data': meal_data
    })

    result.update({
        'interval_data': interval_data
    })

    result.update({
        'breakfast_data': breakfast_data
    })

    result.update({
        'density_data': density_data
    })

    result.update({
        'has_evening_meal_issues': has_evening_meal_issues
    })

    result.update({
        'has_fat_issues': has_fat_issues
    })

    result.update({
        'has_hunger_issues': has_hunger_issues
    })

    result.update({
        'emotional_eating_data': emotional_eating_data
    })

    result.update({
        'has_food_reward_issues':has_food_reward_issues
    })

    result.update({
        'has_snack_issues': has_snack_issues
    })

    result.update({
        'fast_food_data': fast_food_data
    })

    result.update({
        'has_soda_issues': has_soda_issues
    })

    result.update({
        'has_sosage_issues': has_sosage_issues
    })

    result.update({
        'has_smoked_issues': has_smoked_issues
    })

    result.update({
        'has_fat_products_issues': has_fat_products_issues
    })

    result.update({
        'has_sauce_issues': has_sauce_issues
    })

    result.update({
        'has_fried_potato_issues': has_fried_potato_issues
    })

    result.update({
        'has_salted_issues':has_salted_issues
    })

    result.update({
        'has_high_fat_dairy_issues': has_high_fat_dairy_issues
    })

    result.update({
        'has_baking_issues': has_baking_issues
    })

    result.update({
        'has_fruits_veggies_answer': has_fruits_veggies_answer
    })

    result.update({
        'has_grain_issues': has_grain_issues
    })

    result.update({
        'has_legume_issues': has_legume_issues
    })

    result.update({
        'has_lean_meat_issues': has_lean_meat_issues
    })

    result.update({
        'has_seafood_issues': has_seafood_issues
    })

    result.update({
        'dairy_data': dairy_data
    })

    result.update({
        'has_oil_answer': has_oil_answer
    })

    result.update({
        'has_liquid_issues': has_liquid_issues
    })

    result.update({
        'has_salt_addition_issues': has_salt_addition_issues
    })

    result.update({
        'has_special_foof_issues': has_special_foof_issues
    })

    result.update({
        'has_supplements_issues': has_supplements_issues
    })

    # Общие показатели
    result['total_score'] = round(total_score, 2)
    result['rating'] = determine_rating(total_score)

    # Округление значений
    for key in result:
        if isinstance(result[key], float):
            result[key] = round(result[key], 2)
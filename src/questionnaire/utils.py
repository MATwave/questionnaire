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
            'descriptions': ["ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ",
                             "СОН",
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
    category_values, smoking_data, diseases, waist_hip_data, bp_data, cholesterol_data, glucose_data, has_low_activity, has_sleep_issues  = process_responses(responses, bmi_data, user_profile)

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
        has_sleep_issues
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
    cholesterol_data = {'value': None}
    glucose_data = {'value': None, 'unknown': False}
    physical_activity_values = []
    sleep_values = []

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
            waist_hip_data['waist'] = response.numeric_answer if response.numeric_answer else None
        elif response.question.description == "ОКРУЖНОСТЬ (БЕДЕР)":
            waist_hip_data['hip'] = response.numeric_answer if response.numeric_answer else None
        elif response.question.description == "ОБЩИЙ ХОЛЕСТЕРИН":
            if response.numeric_answer is not None:
                cholesterol_data['value'] = float(response.numeric_answer)
                cholesterol_data['unknown'] = False
            else:
                cholesterol_data['unknown'] = True
        elif response.question.description == "УРОВЕНЬ ГЛЮКОЗЫ":
            if response.numeric_answer is not None:
                try:
                    value = float(response.numeric_answer)
                    # Если значение 0 - считаем неизвестным
                    if value == 0.0:
                        glucose_data['unknown'] = True
                        glucose_data['value'] = None
                    else:
                        glucose_data['value'] = value
                        glucose_data['unknown'] = False
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

    # 4. Расчет показателей талии/бедер

    waist_status = 1
    ratio_status = 1

    if waist_hip_data['waist'] and user_profile.gender:
        # Проверка для талии
        if user_profile.gender == 'M':
            if waist_hip_data['waist'] > 102:
                waist_status = 0
            elif waist_hip_data['waist'] > 94:
                waist_status = 0
        else:  # Female
            if waist_hip_data['waist'] > 88:
                waist_status = 0
            elif waist_hip_data['waist'] > 80:
                waist_status = 0

        # Расчет соотношения
        if waist_hip_data['hip'] and waist_hip_data['hip'] > 0:
            ratio = waist_hip_data['waist'] / waist_hip_data['hip']
            if user_profile.gender == 'M' and ratio >= 0.9:
                ratio_status = 0
            elif user_profile.gender == 'F' and ratio >= 0.85:
                ratio_status = 0

    # Добавляем в категорию
    category_values['medico_biological'].extend([waist_status, ratio_status])

    # 5. Расчет показателей артериального давления
    bp_status = get_bp_status(bp_data)  # Получаем статус давления
    bp_score = 0.0

    if bp_status == 'high':
        bp_score = 0.0
    elif bp_status == 'elevated':
        bp_score = 0.5
    elif bp_status == 'normal':
        bp_score = 1.0

    # Добавляем балл давления в категорию
    category_values['medico_biological'].append(bp_score)

    # 6. Общий холестерин
    if cholesterol_data['value'] and cholesterol_data['value'] > 5.5:
        category_values['medico_biological'].append(0.0)
    elif not cholesterol_data['unknown']:
        # Нормальные значения не влияют на оценку
        category_values['medico_biological'].append(1.0)

    #7. глюкоза
    if glucose_data['value'] and glucose_data['value'] > 6.1:
        category_values['medico_biological'].append(0.0)
    elif glucose_data['value'] and glucose_data['value'] > 5.6:
        category_values['medico_biological'].append(0.5)
    else:
        category_values['medico_biological'].append(1.0)

    # двигательная активность
    has_low_activity = any(v in (0, 0.5) for v in physical_activity_values)
    # сон
    has_sleep_issues = any(v in (0, 0.5) for v in sleep_values)

    return category_values, smoking_data, diseases, waist_hip_data, bp_data, cholesterol_data, glucose_data, has_low_activity, has_sleep_issues


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

def update_result(user_profile, result, bmi_data, category_averages, total_score, smoking_data, diseases, waist_hip_data, bp_data, cholesterol_data, glucose_data, physical_activity_data, sleep_data):
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
        'cholesterol_status': 'high' if cholesterol_data.get('value', 0) > 5.5 else 'normal',
        'cholesterol_unknown': cholesterol_data['unknown']
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

    # Общие показатели
    result['total_score'] = round(total_score, 2)
    result['rating'] = determine_rating(total_score)

    # Округление значений
    for key in result:
        if isinstance(result[key], float):
            result[key] = round(result[key], 2)
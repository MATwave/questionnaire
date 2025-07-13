from django.test import TransactionTestCase
from unittest.mock import patch, MagicMock
from questionnaire.models import Question, Answer, AnonymousUserProfile, UserResponse
from questionnaire.utils import (
    calculate_user_rating,
    get_bmi_categories,
    get_question_categories,
    initialize_base_result,
    calculate_bmi_data,
    get_bp_status,
    get_bp_description,
    get_glucose_status,
    get_response_category,
    safe_average,
    determine_rating,
    get_waist_status,
    get_ratio_status
)


class UtilsTest(TransactionTestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.profile = AnonymousUserProfile.objects.create(
            session_key="test_session",
            gender='M',
            age=35,
            height=180,
            weight=80
        )

        # Категории вопросов - добавляем специальный вопрос для числового ответа
        categories = [
            ('stress', "СТРЕСС"),
            ('nutrition', "ПИТАНИЕ"),
            ('medico_biological', "МЕДИКО-БИОЛОГИЧЕСКИЕ ФАКТОРЫ"),
            ('medico_biological', "ОКРУЖНОСТЬ (ТАЛИИ)"),  # Специальный вопрос для числового ответа
            ('lifestyle', "ДВИГАТЕЛЬНАЯ АКТИВНОСТЬ"),
            ('work_assessment', "РАБОЧЕЕ МЕСТО")
        ]

        self.questions = []
        self.answers = []

        for order, (category, desc) in enumerate(categories, start=1):
            # Для вопроса "ОКРУЖНОСТЬ (ТАЛИИ)" устанавливаем is_numeric_input=True
            is_numeric = (desc == "ОКРУЖНОСТЬ (ТАЛИИ)")
            q = Question.objects.create(
                text=f"{category} question",
                description=desc,
                order=order,
                is_numeric_input=is_numeric
            )
            self.questions.append(q)

            if is_numeric:
                # Для числового вопроса создаем UserResponse с numeric_answer
                response = UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q,
                    numeric_answer=95  # Тестовое значение
                )
            else:
                # Для обычных вопросов создаем ответы
                a = Answer.objects.create(
                    text=f"{category} answer",
                    question=q,
                    value=1.0 if category != 'stress' else 0.5
                )
                self.answers.append(a)
                response = UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q
                )
                response.selected_answers.add(a)

    def test_get_question_categories(self):
        categories = get_question_categories()
        self.assertIsInstance(categories, dict)
        self.assertIn('stress', categories)
        self.assertIn('nutrition', categories)
        self.assertEqual(categories['stress']['label'], 'СТРЕСС')

    def test_initialize_base_result(self):
        result = initialize_base_result()
        self.assertEqual(result['medico_biological_avg'], 0.0)
        self.assertEqual(result['bmi_category'], 'Не рассчитан')
        self.assertEqual(result['rating'], 'Нет данных')

    def test_calculate_bmi_data(self):
        # С нормальными данными
        profile = AnonymousUserProfile(height=170, weight=70)
        bmi_data = calculate_bmi_data(profile)
        self.assertAlmostEqual(bmi_data['value'], 24.22, delta=0.1)
        self.assertEqual(bmi_data['category'], "Нормальный ИМТ")

        # С отсутствующими данными
        profile_no_data = AnonymousUserProfile()
        bmi_data = calculate_bmi_data(profile_no_data)
        self.assertEqual(bmi_data['value'], None)
        self.assertEqual(bmi_data['category'], 'Не рассчитан')

        # С некорректными данными
        profile_invalid = AnonymousUserProfile(height=0, weight=70)
        bmi_data = calculate_bmi_data(profile_invalid)
        self.assertEqual(bmi_data['value'], None)

    def test_bp_status_and_description(self):
        # Тестирование статусов давления с правильной структурой данных
        self.assertEqual(get_bp_status({'unknown': True, 'systolic': None, 'diastolic': None}), 'unknown')
        self.assertEqual(get_bp_status({'unknown': False, 'systolic': 120, 'diastolic': 80}), 'normal')
        self.assertEqual(get_bp_status({'unknown': False, 'systolic': 135, 'diastolic': 85}), 'elevated')
        self.assertEqual(get_bp_status({'unknown': False, 'systolic': 150, 'diastolic': 95}), 'high')

        # Тестирование описаний
        self.assertIn("нормальное", get_bp_description({'unknown': False, 'systolic': 120, 'diastolic': 80}))
        self.assertIn("высокое", get_bp_description({'unknown': False, 'systolic': 150, 'diastolic': 95}))
        self.assertIn("неизвестны", get_bp_description({'unknown': True, 'systolic': None, 'diastolic': None}))

    def test_glucose_status(self):
        self.assertEqual(get_glucose_status(None), "unknown")
        self.assertEqual(get_glucose_status(5.0), "норма")
        self.assertEqual(get_glucose_status(5.7), "превышение капиллярной нормы (>5.6 ммоль/л)")
        self.assertEqual(get_glucose_status(6.2),
                         "превышение капиллярной нормы (>5.6 ммоль/л), превышение венозной нормы (>6.1 ммоль/л)")

    def test_response_category_mapping(self):
        categories = get_question_categories()

        # Создаем тестовый объект UserResponse с привязанным Question
        q = Question.objects.create(
            text="ПИТАНИЕ question",
            description="ПИТАНИЕ",
            order=100
        )
        response = UserResponse(
            user_profile=self.profile,
            question=q
        )

        self.assertEqual(get_response_category(response, categories), 'nutrition')

        # Тест для несуществующей категории
        q2 = Question.objects.create(
            text="Unknown question",
            description="НЕСУЩЕСТВУЮЩАЯ КАТЕГОРИЯ",
            order=101
        )
        response2 = UserResponse(
            user_profile=self.profile,
            question=q2
        )
        self.assertIsNone(get_response_category(response2, categories))

    def test_safe_average(self):
        self.assertEqual(safe_average([1, 2, 3]), 2.0)
        self.assertEqual(safe_average([]), 0.0)
        self.assertEqual(safe_average([0.5, 0.5, 1.0]), 0.6667)

    def test_determine_rating(self):
        self.assertEqual(determine_rating(0.9), "Оптимальная")
        self.assertEqual(determine_rating(0.8), "Хорошая")
        self.assertEqual(determine_rating(0.6), "Удовлетворительная")
        self.assertEqual(determine_rating(0.4), "Неудовлетворительная")

    def test_waist_and_ratio_status(self):
        # Мужские значения
        male_profile = AnonymousUserProfile(gender='M')

        # Добавляем тесты для высокого значения талии у мужчин
        waist_status = get_waist_status(male_profile, 102)
        self.assertEqual(waist_status['status'], "Высокое значение")
        self.assertIn("высокий риск", waist_status['description'])

        waist_status = get_waist_status(male_profile, 110)
        self.assertEqual(waist_status['status'], "Высокое значение")

        # Женские значения
        female_profile = AnonymousUserProfile(gender='F')

        # Добавляем тесты для высокого значения талии у женщин
        waist_status = get_waist_status(female_profile, 88)
        self.assertEqual(waist_status['status'], "Высокое значение")
        self.assertIn("высокий риск", waist_status['description'])

        waist_status = get_waist_status(female_profile, 95)
        self.assertEqual(waist_status['status'], "Высокое значение")
        # Проверка соотношения талия/бедро
        ratio_status = get_ratio_status(
            male_profile,
            {'waist': 95, 'hip': 100}
        )
        self.assertEqual(ratio_status['status'], "Повышенное значение")

    def test_high_waist_processing(self):
        # Создаем профиль мужчины с высокой талией
        profile = AnonymousUserProfile.objects.create(
            session_key="high_waist",
            gender='M'
        )

        # Создаем вопрос о талии
        q = Question.objects.create(
            text="Талия вопрос",
            description="ОКРУЖНОСТЬ (ТАЛИИ)",
            is_numeric_input=True
        )

        # Ответ с высоким значением
        UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=105  # Высокое значение для мужчины
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertEqual(rating_data['waist'], 105)
        self.assertEqual(rating_data['waist_status'], "Высокое значение")
        self.assertIn("высокий риск", rating_data['waist_description'])

    def test_smoking_processing(self):
        # Создаем вопросы о курении
        smoking_questions = [
            ("Курение (сигарет в день)", 10),
            ("Курение (лет стажа)", 5)
        ]

        for desc, value in smoking_questions:
            q = Question.objects.create(
                text=desc,
                description=desc,
                is_numeric_input=True
            )
            UserResponse.objects.create(
                user_profile=self.profile,
                question=q,
                numeric_answer=value
            )

        # Пересчитываем рейтинг
        rating_data = calculate_user_rating(self.profile)
        self.assertAlmostEqual(rating_data['smoking_index'], 2.5)

    def test_medico_biological_factors(self):
        # Исправленная структура данных для медицинских вопросов
        medical_questions = [
            ("ОКРУЖНОСТЬ (ТАЛИИ)", 95, "", []),
            ("ОКРУЖНОСТЬ (БЕДЕР)", 100, "", []),
            ("АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ", None, "120/80", []),
            ("ОБЩИЙ ХОЛЕСТЕРИН", 5.0, "", []),
            ("УРОВЕНЬ ГЛЮКОЗЫ", 5.0, "", []),
            ("Имеющиеся заболевания", None, "", ["Диабет"])
        ]

        for desc, num_val, text_val, diseases in medical_questions:
            q = Question.objects.create(
                text=desc,
                description=desc,
                is_numeric_input=(num_val is not None)
            )
            response = UserResponse.objects.create(
                user_profile=self.profile,
                question=q,
                numeric_answer=num_val,
                free_text_answer=text_val  # Теперь передаем пустую строку вместо None
            )
            if diseases:
                for disease in diseases:
                    a = Answer.objects.create(text=disease, question=q)
                    response.selected_answers.add(a)

        # Пересчитываем рейтинг
        rating_data = calculate_user_rating(self.profile)

        # Проверяем медицинские показатели
        self.assertEqual(rating_data['waist'], 95)
        self.assertAlmostEqual(rating_data['waist_hip_ratio'], 0.95)
        self.assertEqual(rating_data['bp_status'], 'normal')
        self.assertEqual(rating_data['cholesterol_value'], 5.0)
        self.assertEqual(rating_data['glucose_value'], 5.0)
        self.assertIn("Диабет", rating_data['existing_diseases'])

    def test_edge_cases(self):
        # Профиль без ответов
        empty_profile = AnonymousUserProfile.objects.create(
            session_key="empty_session"
        )
        rating_data = calculate_user_rating(empty_profile)
        self.assertEqual(rating_data['total_score'], 0.0)
        self.assertEqual(rating_data['rating'], 'Нет данных')

        # Профиль с частичными данными
        partial_profile = AnonymousUserProfile.objects.create(
            session_key="partial_session",
            height=170
        )
        rating_data = calculate_user_rating(partial_profile)
        self.assertEqual(rating_data['bmi'], 'Нет данных')

    def test_bmi_calculation_errors(self):
        # Тест для ZeroDivisionError (рост = 0)
        profile_zero_height = AnonymousUserProfile.objects.create(
            session_key="zero_height",
            height=0,
            weight=80
        )
        bmi_data = calculate_bmi_data(profile_zero_height)
        self.assertEqual(bmi_data['value'], None)
        self.assertEqual(bmi_data['category'], 'Не рассчитан')
        self.assertEqual(bmi_data['risk_level'], 'Не определен')

        # Тест для отрицательных значений
        profile_negative = AnonymousUserProfile.objects.create(
            session_key="negative_values",
            height=-170,
            weight=-70
        )
        bmi_data = calculate_bmi_data(profile_negative)
        self.assertEqual(bmi_data['value'], None)

        # Тест для TypeError (некорректные типы данных) - создаем объект без сохранения в БД
        class MockProfile:
            def __init__(self, height, weight):
                self.height = height
                self.weight = weight

        # Создаем mock-объекты с невалидными данными
        profile_string = MockProfile("не число", "не число")
        profile_none = MockProfile(None, None)

        # Проверяем обработку строковых значений
        bmi_data_str = calculate_bmi_data(profile_string)
        self.assertEqual(bmi_data_str['value'], None)
        self.assertEqual(bmi_data_str['category'], 'Не рассчитан')

        # Проверяем обработку None-значений
        bmi_data_none = calculate_bmi_data(profile_none)
        self.assertEqual(bmi_data_none['value'], None)
        self.assertEqual(bmi_data_none['category'], 'Не рассчитан')

    def test_unknown_cholesterol_handling(self):
        # Создаем вопрос о холестерине с неизвестным значением
        q = Question.objects.create(
            text="Холестерин вопрос",
            description="ОБЩИЙ ХОЛЕСТЕРИН",
            is_numeric_input=True
        )
        # Создаем ответ без числового значения
        UserResponse.objects.create(
            user_profile=self.profile,
            question=q,
            numeric_answer=None
        )

        rating_data = calculate_user_rating(self.profile)
        self.assertTrue(rating_data['cholesterol_unknown'])
        self.assertEqual(rating_data['cholesterol_value'], None)

    def test_unknown_glucose_handling(self):
        # Создаем вопрос о глюкозе с неизвестным значением
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )
        # Создаем ответ без числового значения
        UserResponse.objects.create(
            user_profile=self.profile,
            question=q,
            numeric_answer=0.0  # Специальное значение для неизвестного
        )

        rating_data = calculate_user_rating(self.profile)
        self.assertTrue(rating_data['glucose_unknown'])
        self.assertEqual(rating_data['glucose_value'], None)

    def test_free_text_diseases(self):
        # Создаем вопрос о заболеваниях
        q = Question.objects.create(
            text="Заболевания вопрос",
            description="Имеющиеся заболевания",
            allow_free_text=True
        )
        # Создаем ответ со свободным текстом
        response = UserResponse.objects.create(
            user_profile=self.profile,
            question=q,
            free_text_answer="Мое особое заболевание"
        )

        rating_data = calculate_user_rating(self.profile)
        self.assertIn("Мое особое заболевание", rating_data['existing_diseases'])

    def test_unknown_bp_handling(self):
        # Создаем вопрос о давлении
        q = Question.objects.create(
            text="Давление вопрос",
            description="АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ",
            allow_free_text=True
        )
        # Создаем ответ с некорректным форматом
        UserResponse.objects.create(
            user_profile=self.profile,
            question=q,
            free_text_answer="некорректный формат"
        )

        rating_data = calculate_user_rating(self.profile)
        self.assertEqual(rating_data['bp_status'], 'unknown')
        self.assertIn("необходимо провести измерение", rating_data['bp_description'])

    def test_combined_unknown_values(self):
        # Создаем вопросы с неизвестными значениями
        questions = [
            ("ОБЩИЙ ХОЛЕСТЕРИН", None),
            ("УРОВЕНЬ ГЛЮКОЗЫ", 0.0),
            ("АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ", "некорректный формат")
        ]

        for desc, value in questions:
            q = Question.objects.create(
                text=f"{desc} вопрос",
                description=desc,
                is_numeric_input=(desc != "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ"),
                allow_free_text=(desc == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ")
            )
            if desc == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ":
                UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q,
                    free_text_answer=value
                )
            else:
                UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q,
                    numeric_answer=value
                )

        rating_data = calculate_user_rating(self.profile)
        self.assertTrue(rating_data['cholesterol_unknown'])
        self.assertTrue(rating_data['glucose_unknown'])
        self.assertEqual(rating_data['bp_status'], 'unknown')

    def test_all_question_types_processing(self):
        # Список всех описаний вопросов, которые нужно протестировать
        question_descriptions = [
            "СОН",
            "ЦИФРОВАЯ ГИГИЕНА",
            "ОТПУСК",
            "АЛКОГОЛЬ",
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
            "РАБОТА НА ДОМУ",
            "ПРИЕМЫ ПИЩИ",
            "ВРЕМЯ ПЕРЕРЫВОВ МЕЖДУ ЕДОЙ",
            "ЗАВТРАК",
            "НАИБОЛЕЕ ПЛОТНЫЙ ПРИЕМ ПИЩИ",
            "ЕДА ДО СНА",
            "ВИД ЖИРОВ",
            "ГОЛОД",
            "ЭМОЦИОНАЛЬНЫЕ ПЕРЕКУСЫ",
            "ПООЩРЕНИЕ ИЛИ НАКАЗАНИЕ ЕДОЙ",
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
            "БАДЫ"
        ]

        # Создаем вопросы и ответы для каждого типа
        for index, desc in enumerate(question_descriptions):
            q = Question.objects.create(
                text=f"Тестовый вопрос: {desc}",
                description=desc,
                order=1000 + index  # Уникальный порядок
            )

            # Для вопросов, которые просто отмечают факт наличия ответа
            if desc in ["ОТПУСК", "АЛКОГОЛЬ", "КОЛИЧЕСТВО ФРУКТОВ И ОВОЩЕЙ", "РАСТИТЕЛЬНЫЕ МАСЛА"]:
                # Создаем обычный ответ
                a = Answer.objects.create(
                    text=f"Тестовый ответ: {desc}",
                    question=q,
                    value=1.0
                )
                response = UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q
                )
                response.selected_answers.add(a)
            else:
                # Для вопросов, которые собирают значения
                # Создаем ответ с "проблемным" значением (0 или 0.5)
                a = Answer.objects.create(
                    text=f"Тестовый ответ: {desc}",
                    question=q,
                    value=0.0
                )
                response = UserResponse.objects.create(
                    user_profile=self.profile,
                    question=q
                )
                response.selected_answers.add(a)

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(self.profile)

        # Проверяем установленные флаги
        self.assertTrue(rating_data['sleep_alert'])
        self.assertTrue(rating_data['digital_hygiene_alert'])
        self.assertTrue(rating_data['vacation_alert'])
        self.assertTrue(rating_data['alcohol_alert'])
        self.assertTrue(rating_data['has_physical_load_issues'])
        self.assertTrue(rating_data['has_work_pace_issues'])
        self.assertTrue(rating_data['has_emotional_load_issues'])
        self.assertTrue(rating_data['has_fatigue_issues'])
        self.assertTrue(rating_data['has_schedule_issues'])
        self.assertTrue(rating_data['has_digital_work_issues'])
        self.assertTrue(rating_data['critical_data']['has_critical_0'])
        self.assertTrue(rating_data['extra_effort_data']['has_extra_0'])
        self.assertTrue(rating_data['has_breaks_issues'])
        self.assertTrue(rating_data['has_lunch_issues'])
        self.assertTrue(rating_data['remote_work_data']['has_remote_0'])
        self.assertTrue(rating_data['meal_data']['has_meal_0'])
        self.assertTrue(rating_data['interval_data']['has_interval_0'])
        self.assertTrue(rating_data['breakfast_data']['has_breakfast_0'])
        self.assertTrue(rating_data['density_data']['has_density_0'])
        self.assertTrue(rating_data['has_evening_meal_issues'])
        self.assertTrue(rating_data['has_fat_issues'])
        self.assertTrue(rating_data['has_hunger_issues'])
        self.assertTrue(rating_data['emotional_eating_data']['has_emotional_eating_0'])
        self.assertTrue(rating_data['has_food_reward_issues'])
        self.assertTrue(rating_data['has_snack_issues'])
        self.assertTrue(rating_data['fast_food_data']['has_fast_food_0'])
        self.assertTrue(rating_data['has_soda_issues'])
        self.assertTrue(rating_data['has_sosage_issues'])
        self.assertTrue(rating_data['has_smoked_issues'])
        self.assertTrue(rating_data['has_fat_products_issues'])
        self.assertTrue(rating_data['has_sauce_issues'])
        self.assertTrue(rating_data['has_fried_potato_issues'])
        self.assertTrue(rating_data['has_salted_issues'])
        self.assertTrue(rating_data['has_high_fat_dairy_issues'])
        self.assertTrue(rating_data['has_baking_issues'])
        self.assertTrue(rating_data['has_fruits_veggies_answer'])
        self.assertTrue(rating_data['has_grain_issues'])
        self.assertTrue(rating_data['has_legume_issues'])
        self.assertTrue(rating_data['has_lean_meat_issues'])
        self.assertTrue(rating_data['has_seafood_issues'])
        self.assertTrue(rating_data['dairy_data']['has_dairy_0'])
        self.assertTrue(rating_data['has_oil_answer'])
        self.assertTrue(rating_data['has_liquid_issues'])
        self.assertTrue(rating_data['has_salt_addition_issues'])
        self.assertTrue(rating_data['has_special_foof_issues'])
        self.assertTrue(rating_data['has_supplements_issues'])

    def test_high_glucose_processing(self):
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="high_glucose",
            gender='M',
            height=180,  # Добавляем рост и вес
            weight=80  # чтобы ИМТ рассчитывался нормально
        )

        # Создаем вопрос о глюкозе
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )

        # Ответ с высоким значением (>6.1)
        UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=6.5
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertEqual(rating_data['glucose_value'], 6.5)
        self.assertIn("превышение венозной нормы", rating_data['glucose_status'])

        # Проверяем балл глюкозы в контексте других показателей
        # Должен быть 0.0 за глюкозу + другие баллы
        # Не проверяем точное среднее, так как есть другие факторы

    def test_elevated_glucose_processing(self):
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="elevated_glucose",
            gender='F',
            height=170,  # Добавляем рост и вес
            weight=60  # чтобы ИМТ рассчитывался нормально
        )

        # Создаем вопрос о глюкозе
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )

        # Ответ с повышенным значением (5.6 < value ≤ 6.1)
        UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=5.8
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertEqual(rating_data['glucose_value'], 5.8)
        self.assertIn("превышение капиллярной нормы", rating_data['glucose_status'])

        # Проверяем, что балл глюкозы добавлен правильно
        # В реальной системе можно проверить через логи
        # Или добавить дополнительные проверки

    def test_normal_glucose_processing(self):
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="normal_glucose",
            gender='M',
            height=175,  # Добавляем рост и вес
            weight=75  # чтобы ИМТ рассчитывался нормально
        )

        # Создаем вопрос о глюкозе
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )

        # Ответ с нормальным значением (≤5.6)
        UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=5.0
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertEqual(rating_data['glucose_value'], 5.0)
        self.assertEqual(rating_data['glucose_status'], "норма")

        # Проверяем, что балл глюкозы добавлен правильно
        # В реальной системе можно проверить через логи
        # Или добавить дополнительные проверки

    def test_female_good_waist_hip_ratio(self):
        """Тест для женщины с хорошим соотношением талия/бедро (<0.85)"""
        # Создаем профиль женщины
        profile = AnonymousUserProfile.objects.create(
            session_key="female_good_ratio",
            gender='F',
            height=170,  # Добавляем рост
            weight=60  # и вес для расчета ИМТ
        )

        # Создаем вопрос о талии
        q_waist = Question.objects.create(
            text="Талия вопрос",
            description="ОКРУЖНОСТЬ (ТАЛИИ)",
            is_numeric_input=True
        )
        # Ответ: талия 75 см
        UserResponse.objects.create(
            user_profile=profile,
            question=q_waist,
            numeric_answer=75
        )

        # Создаем вопрос о бедрах
        q_hip = Question.objects.create(
            text="Бедра вопрос",
            description="ОКРУЖНОСТЬ (БЕДЕР)",
            is_numeric_input=True
        )
        # Ответ: бедра 95 см -> соотношение 75/95 = 0.789 ≈ 0.79
        UserResponse.objects.create(
            user_profile=profile,
            question=q_hip,
            numeric_answer=95
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем данные
        self.assertEqual(rating_data['waist'], 75)
        self.assertEqual(rating_data['hip'], 95)
        self.assertAlmostEqual(rating_data['waist_hip_ratio'], 0.79, places=2)

        # Проверяем обработку соотношения
        self.assertEqual(rating_data['ratio_status'], "Норма")
        self.assertIn("Риск сопутствующих заболеваний снижен", rating_data['ratio_description'])

    def test_female_bad_waist_hip_ratio(self):
        """Тест для женщины с плохим соотношением талия/бедро (>=0.85)"""
        # Создаем профиль женщины
        profile = AnonymousUserProfile.objects.create(
            session_key="female_bad_ratio",
            gender='F',
            height=170,  # Добавляем рост
            weight=60  # и вес для расчета ИМТ
        )

        # Создаем вопрос о талии
        q_waist = Question.objects.create(
            text="Талия вопрос",
            description="ОКРУЖНОСТЬ (ТАЛИИ)",
            is_numeric_input=True
        )
        # Ответ: талия 85 см
        UserResponse.objects.create(
            user_profile=profile,
            question=q_waist,
            numeric_answer=85
        )

        # Создаем вопрос о бедрах
        q_hip = Question.objects.create(
            text="Бедра вопрос",
            description="ОКРУЖНОСТЬ (БЕДЕР)",
            is_numeric_input=True
        )
        # Ответ: бедра 95 см -> соотношение 85/95 = 0.8947 ≈ 0.89
        UserResponse.objects.create(
            user_profile=profile,
            question=q_hip,
            numeric_answer=95
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем данные (с округлением до 2 знаков)
        self.assertEqual(rating_data['waist'], 85)
        self.assertEqual(rating_data['hip'], 95)
        self.assertAlmostEqual(rating_data['waist_hip_ratio'], 0.89, places=2)

        # Проверяем обработку соотношения
        self.assertEqual(rating_data['ratio_status'], "Повышенное значение")
        self.assertIn("высокий риск развития метаболических нарушений", rating_data['ratio_description'])

    def test_cholesterol_processing_exception(self):
        """Тест обработки исключения при преобразовании холестерина"""
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="cholesterol_exception",
            gender='M'
        )

        # Создаем вопрос о холестерине
        q = Question.objects.create(
            text="Холестерин вопрос",
            description="ОБЩИЙ ХОЛЕСТЕРИН",
            is_numeric_input=True
        )

        # Создаем ответ с валидным значением
        response = UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=5.0
        )

        # Создаем мок для ответа
        mock_response = MagicMock()
        mock_response.question.description = "ОБЩИЙ ХОЛЕСТЕРИН"
        mock_response.numeric_answer = "invalid"  # Нечисловое значение

        # Создаем мок для QuerySet
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_queryset.__iter__.return_value = [mock_response]
        mock_queryset.prefetch_related.return_value = mock_queryset

        with patch('questionnaire.utils.UserResponse.objects.filter') as mock_filter:
            mock_filter.return_value = mock_queryset

            # Рассчитываем рейтинг
            rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertTrue(rating_data['cholesterol_unknown'])
        self.assertIsNone(rating_data['cholesterol_value'])

    def test_glucose_processing_exception(self):
        """Тест обработки исключения при преобразовании глюкозы"""
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="glucose_exception",
            gender='F'
        )

        # Создаем вопрос о глюкозе
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )

        # Создаем ответ с валидным значением
        response = UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=5.0
        )

        # Создаем мок для ответа
        mock_response = MagicMock()
        mock_response.question.description = "УРОВЕНЬ ГЛЮКОЗЫ"
        mock_response.numeric_answer = "invalid"  # Нечисловое значение

        # Создаем мок для QuerySet
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_queryset.__iter__.return_value = [mock_response]
        mock_queryset.prefetch_related.return_value = mock_queryset

        with patch('questionnaire.utils.UserResponse.objects.filter') as mock_filter:
            mock_filter.return_value = mock_queryset

            # Рассчитываем рейтинг
            rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertTrue(rating_data['glucose_unknown'])
        self.assertIsNone(rating_data['glucose_value'])

    def test_glucose_processing_none_answer(self):
        """Тест обработки None-ответа на глюкозу"""
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="glucose_none",
            gender='M'
        )

        # Создаем вопрос о глюкозе
        q = Question.objects.create(
            text="Глюкоза вопрос",
            description="УРОВЕНЬ ГЛЮКОЗЫ",
            is_numeric_input=True
        )

        # Создаем ответ с None-значением
        response = UserResponse.objects.create(
            user_profile=profile,
            question=q,
            numeric_answer=None
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertTrue(rating_data['glucose_unknown'])
        self.assertIsNone(rating_data['glucose_value'])

    def test_bp_processing_exception(self):
        """Тест обработки исключения при преобразовании давления"""
        # Создаем профиль
        profile = AnonymousUserProfile.objects.create(
            session_key="bp_exception",
            gender='M'
        )

        # Создаем вопрос о давлении
        q = Question.objects.create(
            text="Давление вопрос",
            description="АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ",
            allow_free_text=True
        )

        # Создаем ответ с невалидным значением
        response = UserResponse.objects.create(
            user_profile=profile,
            question=q,
            free_text_answer="invalid/invalid"
        )

        # Рассчитываем рейтинг
        rating_data = calculate_user_rating(profile)

        # Проверяем обработку
        self.assertTrue(rating_data['bp_data']['unknown'])
        self.assertEqual(rating_data['bp_status'], 'unknown')
        self.assertIn("необходимо провести измерение", rating_data['bp_description'])
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from questionnaire.models import Question, AnonymousUserProfile, UserResponse, Answer


class AdminTests(TransactionTestCase):
    def setUp(self):
        # Создание суперпользователя
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass',
            email='admin@example.com'
        )
        self.client.login(username='admin', password='adminpass')

        # Создание базовых объектов
        self.question = Question.objects.create(
            text="Admin test question",
            order=1
        )
        self.numeric_question = Question.objects.create(
            text="Numeric question",
            order=2,
            is_numeric_input=True
        )
        self.free_text_question = Question.objects.create(
            text="Free text question",
            order=3,
            allow_free_text=True
        )

        # Профили пользователей
        self.profile = AnonymousUserProfile.objects.create(
            session_key="admin_test_session"
        )
        self.empty_profile = AnonymousUserProfile.objects.create(
            session_key="empty_session"
        )
        self.bmi_profile = AnonymousUserProfile.objects.create(
            session_key="bmi_calc_session",
            height=0,  # Для теста деления на ноль
            weight=70
        )

        # Ответы
        self.response = UserResponse.objects.create(
            user_profile=self.profile,
            question=self.question
        )
        self.numeric_response = UserResponse.objects.create(
            user_profile=self.profile,
            question=self.numeric_question,
            numeric_answer=42
        )
        self.free_text_response = UserResponse.objects.create(
            user_profile=self.profile,
            question=self.free_text_question,
            free_text_answer="Additional comment"
        )

    # Тест для экспорта CSV с разными сценариями
    def test_export_csv_edge_cases(self):
        # Добавляем ответ для профиля с нулевым ростом
        UserResponse.objects.create(
            user_profile=self.bmi_profile,
            question=self.question
        )

        url = reverse('admin:questionnaire_question_changelist')
        data = {
            'action': 'export_responses_csv',
            '_selected_action': [
                self.question.id,
                self.numeric_question.id,
                self.free_text_question.id
            ]
        }
        response = self.client.post(url, data, follow=True)

        # Проверка успешного экспорта
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="responses.csv"',
                      response['Content-Disposition'])

        # Проверка контента
        content = response.content.decode('utf-8').splitlines()
        headers = content[0].split('\t')

        # Находим строку для профиля с BMI ошибкой по весу
        bmi_row = None
        for row in content[1:]:
            if '70' in row:  # Вес bmi_profile
                bmi_row = row.split('\t')
                break

        # Проверяем что строка найдена
        self.assertIsNotNone(bmi_row, "Строка для профиля с нулевым ростом не найдена в экспорте CSV")

        # Проверка ошибки расчета ИМТ
        bmi_index = headers.index("ИМТ")
        self.assertEqual(bmi_row[bmi_index], 'Ошибка расчета')

        # Находим строку для основного профиля по свободному тексту
        main_row = None
        for row in content[1:]:
            if 'Additional comment' in row:
                main_row = row.split('\t')
                break

        # Проверяем что строка найдена
        self.assertIsNotNone(main_row, "Строка для основного профиля не найдена в экспорте CSV")

        # Проверка числового ответа
        numeric_index = headers.index("Numeric question")
        self.assertEqual(main_row[numeric_index], '42.0')

        # Проверка свободного текста
        free_text_index = headers.index("Free text question")
        self.assertIn("Additional comment", main_row[free_text_index])

        # Проверка отсутствия ответа
        admin_question_index = headers.index("Admin test question")
        self.assertEqual(main_row[admin_question_index], "")

    def test_empty_profiles_in_export(self):
        # Полная очистка всех объектов
        UserResponse.objects.all().delete()
        AnonymousUserProfile.objects.all().delete()
        Question.objects.all().delete()  # Удаляем все вопросы

        # Пересоздаем необходимые вопросы
        self.question = Question.objects.create(
            text="Admin test question",
            order=1
        )
        other_question = Question.objects.create(
            text="Other question",
            order=2
        )

        # Создаем тестовые профили с уникальными данными
        empty_profile = AnonymousUserProfile.objects.create(
            session_key="empty_test_session",
            gender='F',  # Женский
            age=20
        )

        profile_with_selected_response = AnonymousUserProfile.objects.create(
            session_key="selected_response_session",
            gender='M',  # Мужской
            age=25
        )

        profile_with_unselected_response = AnonymousUserProfile.objects.create(
            session_key="unselected_response_session",
            gender='O',  # Другой
            age=30
        )

        # Создаем ответы
        UserResponse.objects.create(
            user_profile=profile_with_selected_response,
            question=self.question
        )
        UserResponse.objects.create(
            user_profile=profile_with_unselected_response,
            question=other_question
        )

        url = reverse('admin:questionnaire_question_changelist')
        data = {
            'action': 'export_responses_csv',
            '_selected_action': [self.question.id]
        }
        response = self.client.post(url, data, follow=True)
        content = response.content.decode('utf-8').splitlines()

        # Должно быть 2 строки: заголовок + 1 профиль с ответами
        self.assertEqual(len(content), 2,
                         f"Ожидается 2 строки (заголовок + данные), получено {len(content)}: {content}")

        data_row = content[1].split('\t')

        # Индексы колонок
        gender_index = 1
        age_index = 2

        # Проверяем что профиль с выбранным вопросом экспортировался
        self.assertEqual(data_row[gender_index], 'Мужской')
        self.assertEqual(data_row[age_index], '25')

        # Проверяем что профиль без ответов не экспортировался
        # Проверяем конкретные колонки, а не всю строку
        self.assertNotEqual(data_row[gender_index], 'Женский')
        self.assertNotEqual(data_row[age_index], '20')

        # Проверяем что профиль с НЕвыбранным вопросом не экспортировался
        self.assertNotEqual(data_row[gender_index], 'Другой')
        self.assertNotEqual(data_row[age_index], '30')

    # Тест для админки числовых вопросов
    def test_numeric_question_admin(self):
        url = reverse('admin:questionnaire_question_change', args=[self.numeric_question.id])
        response = self.client.get(url)

        # Проверка отсутствия дополнительных настроек
        self.assertNotContains(response, "Дополнительные настройки")

        # Проверка отсутствия инлайнов через CSS-класс
        self.assertNotContains(response, 'class="inline-group"')

    # Тест UserResponseAdmin
    def test_user_response_admin(self):
        # Добавляем ответы к базовому вопросу
        answer1 = Answer.objects.create(question=self.question, text="Answer 1")
        answer2 = Answer.objects.create(question=self.question, text="Answer 2")
        self.response.selected_answers.add(answer1, answer2)

        # Тестируем список ответов
        url = reverse('admin:questionnaire_userresponse_changelist')
        response = self.client.get(url)

        # Проверка форматирования ответов
        self.assertContains(response, "Answer 1, Answer 2")

        # Проверка данных пользователя
        self.assertContains(response, "-, - лет, - см, - кг")

        # Обновляем профиль
        self.profile.gender = 'M'
        self.profile.age = 30
        self.profile.height = 180.0
        self.profile.weight = 75.0
        self.profile.save()

        # Проверка обновленных данных (с учетом форматирования float)
        response = self.client.get(url)
        self.assertContains(response, "M, 30 лет, 180.0 см, 75.0 кг")

    # Существующие тесты остаются без изменений
    def test_question_admin(self):
        url = reverse('admin:questionnaire_question_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Проверка страницы редактирования
        edit_url = reverse('admin:questionnaire_question_change', args=[self.question.id])
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

    def test_export_csv(self):
        # Создаем тестовый ответ
        UserResponse.objects.create(
            user_profile=self.profile,
            question=self.question
        )

        url = reverse('admin:questionnaire_question_changelist')
        data = {
            'action': 'export_responses_csv',
            '_selected_action': [self.question.id]
        }
        response = self.client.post(url, data, follow=True)

        # Проверяем экспорт CSV
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="responses.csv"',
                      response['Content-Disposition'])

    def test_export_csv_bmi_calculation(self):
        # Создаем профиль с корректными данными для расчета ИМТ
        valid_bmi_profile = AnonymousUserProfile.objects.create(
            session_key="valid_bmi_session",
            height=180,
            weight=75
        )
        UserResponse.objects.create(
            user_profile=valid_bmi_profile,
            question=self.question
        )

        url = reverse('admin:questionnaire_question_changelist')
        data = {
            'action': 'export_responses_csv',
            '_selected_action': [self.question.id]
        }
        response = self.client.post(url, data, follow=True)

        content = response.content.decode('utf-8').splitlines()
        headers = content[0].split('\t')

        # Находим строку профиля по уникальным данным
        bmi_row = None
        for row in content[1:]:
            if '180' in row and '75' in row:
                bmi_row = row.split('\t')
                break

        self.assertIsNotNone(bmi_row, "Строка для профиля с корректным ИМТ не найдена")

        # Проверяем рассчитанный ИМТ
        bmi_index = headers.index("ИМТ")
        self.assertEqual(bmi_row[bmi_index], '23.1')  # 75/(1.80**2) = 23.148 ≈ 23.1
from django.test import TransactionTestCase
from django.test import Client
from django.urls import reverse
from django.contrib.sessions.models import Session

from questionnaire.models import AnonymousUserProfile, Question, Answer, UserResponse


class QuestionnaireViewsTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client = Client()
        response = self.client.get(reverse('home'))
        self.session_key = self.client.session.session_key

        self.profile = AnonymousUserProfile.objects.create(
            session_key=self.session_key,
            gender='M',
            age='30',  # Исправлено на строку
            height='180',
            weight='80'
        )

        self.question1 = Question.objects.create(
            text="Question 1",
            order=1
        )
        self.question2 = Question.objects.create(
            text="Question 2",
            order=2
        )
        self.answer = Answer.objects.create(
            text="Test answer",
            question=self.question1,
            value=1.0
        )

    def test_thank_you_view_no_session(self):
        self.client.cookies.pop('sessionid', None)  # Удаляем сессию
        response = self.client.get(reverse('thank_you_view'))
        self.assertRedirects(response, reverse('home'))

    def test_user_profile_view_new_session(self):
        # Удаляем существующую сессию
        self.client.cookies.pop('sessionid', None)
        response = self.client.get(reverse('user_profile_view'))
        self.assertIsNotNone(response.wsgi_request.session.session_key)

    def test_user_profile_view_thank_you_redirect(self):
        self.profile.filled_survey = True
        self.profile.save()
        response = self.client.get(reverse('user_profile_view'))
        self.assertRedirects(response, reverse('thank_you_view'))

    def test_user_profile_view_questionnaire_redirect(self):
        response = self.client.get(reverse('user_profile_view'))
        self.assertRedirects(
            response,
            reverse('questionnaire_start'),
            fetch_redirect_response=False
        )

    def test_questionnaire_no_session(self):
        self.client.cookies.pop('sessionid', None)  # Удаляем сессию
        response = self.client.get(reverse('questionnaire_view', args=[1]))
        self.assertRedirects(response, reverse('user_profile_view'))

    def test_questionnaire_thank_you_redirect_completed(self):
        self.profile.filled_survey = True
        self.profile.save()
        response = self.client.get(reverse('questionnaire_view', args=[1]))
        self.assertRedirects(response, reverse('thank_you_view'))

    def test_questionnaire_thank_you_no_questions(self):
        Question.objects.all().delete()
        response = self.client.get(reverse('questionnaire_view', args=[1]))
        self.assertRedirects(
            response,
            reverse('thank_you_view'),
            fetch_redirect_response=False
        )

    def test_questionnaire_redirect_to_first(self):
        # Вызываем без номера вопроса
        response = self.client.get(reverse('questionnaire_start'))
        first_question = Question.objects.order_by('order').first()
        expected_url = reverse('questionnaire_view', args=[first_question.order])
        self.assertRedirects(response, expected_url)

    def test_questionnaire_completion_after_last(self):
        # Убедимся, что у последнего вопроса есть ответ
        last_question = Question.objects.order_by('-order').first()
        if not last_question.answers.exists():
            Answer.objects.create(
                text="Last Question Answer",
                question=last_question,
                value=1.0
            )

        url = reverse('questionnaire_view', args=[last_question.order])

        answer = last_question.answers.first()
        response = self.client.post(url, {'answers': [answer.id]})

        self.assertRedirects(response, reverse('thank_you_view'))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.filled_survey)

    def test_user_profile_creation_on_post(self):
        AnonymousUserProfile.objects.all().delete()
        response = self.client.post(reverse('user_profile_view'), {
            'gender': 'F',
            'age': '25',  # Передаем как строку (как из формы)
            'height': '165',
            'weight': '60'
        })
        self.assertEqual(AnonymousUserProfile.objects.count(), 1)
        profile = AnonymousUserProfile.objects.first()

        # Проверяем как число (так хранится в базе)
        self.assertIsInstance(profile.age, int)
        self.assertEqual(profile.age, 25)

    def test_user_profile_view(self):
        # Удаляем существующий профиль для этого теста
        AnonymousUserProfile.objects.filter(session_key=self.session_key).delete()

        # GET запрос должен вернуть 200, так как профиля нет
        response = self.client.get(reverse('user_profile_view'))
        self.assertEqual(response.status_code, 200)

        # POST запрос с данными
        response = self.client.post(reverse('user_profile_view'), {
            'gender': 'F',
            'age': 25,
            'height': 165,
            'weight': 60
        })

        # Проверяем редирект без следования за ним
        self.assertRedirects(response, reverse('questionnaire_start'), fetch_redirect_response=False)

        # Проверяем, что профиль создан
        self.assertTrue(AnonymousUserProfile.objects.filter(session_key=self.session_key).exists())

    def test_questionnaire_view(self):
        # Проверяем, что сессия существует
        self.assertTrue(Session.objects.filter(session_key=self.session_key).exists())

        # Проверяем, что профиль существует и привязан к сессии
        self.assertTrue(AnonymousUserProfile.objects.filter(session_key=self.session_key).exists())

        # Создаем URL для первого вопроса
        url = reverse('questionnaire_view', args=[self.question1.order])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_thank_you_view(self):
        # Помечаем профиль как заполненный
        self.profile.filled_survey = True
        self.profile.save()

        # Создаем ответ пользователя
        response_obj = UserResponse.objects.create(
            user_profile=self.profile,
            question=self.question1
        )
        response_obj.selected_answers.add(self.answer)

        # Убедимся, что ответ создан
        self.assertEqual(UserResponse.objects.count(), 1)

        # Выполняем запрос
        response = self.client.get(reverse('thank_you_view'))

        self.assertEqual(response.status_code, 200)

    def test_thank_you_view_redirect_if_not_filled(self):
        # Убедимся, что профиль не заполнил опрос
        self.profile.filled_survey = False
        self.profile.save()

        # Выполняем запрос
        response = self.client.get(reverse('thank_you_view'))

        # Проверяем редирект на questionnaire_start
        self.assertRedirects(
            response,
            reverse('questionnaire_start'),
            fetch_redirect_response=False
        )

    def test_thank_you_view_success(self):
        # Убедимся, что профиль заполнил опрос
        self.profile.filled_survey = True
        self.profile.save()

        # Выполняем запрос
        response = self.client.get(reverse('thank_you_view'))

        # Проверяем успешный ответ
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Спасибо за прохождение анкеты!")

class QuestionnairePostProcessingTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client = Client()
        response = self.client.get(reverse('home'))
        self.session_key = self.client.session.session_key

        self.profile = AnonymousUserProfile.objects.create(
            session_key=self.session_key,
            gender='M',
            age=30,
            height=180,
            weight=80
        )

        self.numeric_question = Question.objects.create(
            text="Numeric Question",
            order=1,
            is_numeric_input=True,
            is_required=True
        )

        self.bp_question = Question.objects.create(
            text="Артериальное давление",
            order=2,
            allow_free_text=True,
            is_required=True,
            description="АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ"
        )

        self.multi_choice_question = Question.objects.create(
            text="Multi Choice",
            order=3,
            is_multiple_choice=True
        )

        self.free_text_question = Question.objects.create(
            text="Free Text Question",
            order=4,
            allow_free_text=True
        )

        self.answer1 = Answer.objects.create(
            text="Option 1",
            question=self.multi_choice_question
        )
        self.answer2 = Answer.objects.create(
            text="Option 2",
            question=self.multi_choice_question
        )

    def test_valid_numeric_answer(self):
        url = reverse('questionnaire_view', args=[self.numeric_question.order])
        response = self.client.post(url, {'numeric_answer': '5.5'})
        self.assertEqual(response.status_code, 302)

    def test_invalid_numeric_answer_negative(self):
        url = reverse('questionnaire_view', args=[self.numeric_question.order])
        response = self.client.post(url, {'numeric_answer': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Значение не может быть отрицательным")

    def test_cholesterol_validation(self):
        cholesterol_q = Question.objects.create(
            text="Cholesterol",
            order=5,
            is_numeric_input=True,
            is_required=True,
            description="ОБЩИЙ ХОЛЕСТЕРИН"
        )

        url = reverse('questionnaire_view', args=[cholesterol_q.order])

        response = self.client.post(url, {'numeric_answer': '1.5'})
        self.assertContains(response, "Проверьте значение (допустимо 2.0-30.0 ммоль/л)")

        response = self.client.post(url, {'numeric_answer': '35'})
        self.assertContains(response, "Проверьте значение (допустимо 2.0-30.0 ммоль/л)")

        response = self.client.post(url, {'numeric_answer': '5.5'})
        self.assertEqual(response.status_code, 302)

    def test_blood_pressure_validation(self):
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        response = self.client.post(url, {'free_text': '120/80'})
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {'free_text': 'не знаю'})
        self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {'free_text': '120-80'})
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

        response = self.client.post(url, {'free_text': '300/200'})
        self.assertContains(response, "Проверьте корректность значений")

    def test_valid_free_text_with_single_option(self):
        ft_free_text_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.free_text_question
        )

        url = reverse('questionnaire_view', args=[self.free_text_question.order])
        response = self.client.post(url, {
            'answers': [ft_free_text_answer.id],
            'free_text': 'Мой вариант'
        })
        self.assertEqual(response.status_code, 302)

        response_obj = UserResponse.objects.get(
            user_profile=self.profile,
            question=self.free_text_question
        )
        # Проверяем что свободный текст сохранен
        self.assertEqual(response_obj.free_text_answer, 'Мой вариант')

        # Ожидаем, что выбранный ответ "Свой вариант" сохранен
        self.assertEqual(response_obj.selected_answers.count(), 1)
        self.assertEqual(response_obj.selected_answers.first().text, "Свой вариант")

    def test_valid_free_text_without_option(self):
        # Создаем вопрос, но НЕ создаем ответ "Свой вариант"
        free_text_only_question = Question.objects.create(
            text="Free Text Only Question",
            order=5,
            allow_free_text=True
        )

        url = reverse('questionnaire_view', args=[free_text_only_question.order])
        response = self.client.post(url, {
            'free_text': 'Мой вариант'
        })
        self.assertEqual(response.status_code, 302)

        response_obj = UserResponse.objects.get(
            user_profile=self.profile,
            question=free_text_only_question
        )
        self.assertEqual(response_obj.free_text_answer, 'Мой вариант')
        self.assertEqual(response_obj.selected_answers.count(), 0)

    def test_free_text_with_option_selection(self):
        ft_answer1 = Answer.objects.create(
            text="Regular Option",
            question=self.free_text_question
        )
        ft_free_text_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.free_text_question
        )

        url = reverse('questionnaire_view', args=[self.free_text_question.order])

        # Выбор обычного + свободного варианта
        response = self.client.post(url, {
            'answers': [ft_answer1.id, ft_free_text_answer.id],
            'free_text': 'Мой вариант'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Нельзя выбирать другие варианты вместе с &#x27;Свой вариант&#x27;")

        # Только свободный вариант
        response = self.client.post(url, {
            'answers': [ft_free_text_answer.id],
            'free_text': 'Мой вариант'
        })
        self.assertEqual(response.status_code, 302)

    def test_required_field_validation(self):
        url = reverse('questionnaire_view', args=[self.numeric_question.order])
        response = self.client.post(url, {})
        self.assertContains(response, "Введите числовое значение")

        url = reverse('questionnaire_view', args=[self.multi_choice_question.order])
        response = self.client.post(url, {})
        self.assertContains(response, "Выберите вариант")

    def test_answer_saving(self):
        url = reverse('questionnaire_view', args=[self.numeric_question.order])
        self.client.post(url, {'numeric_answer': '7.5'})
        response = UserResponse.objects.get(
            user_profile=self.profile,
            question=self.numeric_question
        )
        self.assertEqual(response.numeric_answer, 7.5)

        url = reverse('questionnaire_view', args=[self.multi_choice_question.order])
        self.client.post(url, {'answers': [self.answer1.id, self.answer2.id]})
        response = UserResponse.objects.get(
            user_profile=self.profile,
            question=self.multi_choice_question
        )
        self.assertEqual(response.selected_answers.count(), 2)

    def test_questionnaire_completion(self):
        self.client.post(
            reverse('questionnaire_view', args=[self.numeric_question.order]),
            {'numeric_answer': '5'}
        )
        self.client.post(
            reverse('questionnaire_view', args=[self.bp_question.order]),
            {'free_text': '120/80'}
        )
        self.client.post(
            reverse('questionnaire_view', args=[self.multi_choice_question.order]),
            {'answers': [self.answer1.id]}
        )

        # Создаем ответ для свободного текста
        ft_free_text_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.free_text_question
        )
        response = self.client.post(
            reverse('questionnaire_view', args=[self.free_text_question.order]),
            {'answers': [ft_free_text_answer.id], 'free_text': 'Мой ответ'}
        )

        self.assertRedirects(response, reverse('thank_you_view'))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.filled_survey)

    def test_invalid_numeric_string(self):
        """Проверка обработки некорректного числового ввода"""
        url = reverse('questionnaire_view', args=[self.numeric_question.order])
        response = self.client.post(url, {'numeric_answer': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите корректное число")

    def test_blood_pressure_invalid_format(self):
        """Проверка обработки неверного формата давления"""
        # Создаем ответ "Свой вариант" для давления
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Неправильный формат (не соответствует шаблону)
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': '120-80'  # Неправильный разделитель
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

    def test_blood_pressure_invalid_numbers(self):
        """Проверка обработки нечисловых значений в давлении"""
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Буквы вместо цифр
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': 'abc/def'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

    def test_blood_pressure_required_empty(self):
        """Проверка обязательного поля для артериального давления"""
        # Создаем ответ "Свой вариант" для давления
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])
        response = self.client.post(url, {
            'answers': [bp_answer.id],  # Выбираем "Свой вариант"
            'free_text': ''  # Пустое значение
        })
        self.assertEqual(response.status_code, 200)
        # Проверяем часть сообщения без кавычек
        self.assertContains(response, "Введите значение артериального давления")

    def test_blood_pressure_too_many_numbers(self):
        """Проверка обработки слишком большого количества чисел в давлении"""
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Три числа вместо двух
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': '120/80/90'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

    def test_blood_pressure_non_integer_values(self):
        """Проверка обработки нецелочисленных значений в давлении"""
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Дробные числа вместо целых
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': '120.5/80.2'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

    def test_blood_pressure_mixed_format(self):
        """Проверка обработки смешанного формата с числами и текстом"""
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Число + текст
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': '12a/80b'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Введите давление в формате ЧИСЛО/ЧИСЛО")

    def test_blood_pressure_out_of_range_values(self):
        """Проверка обработки значений давления вне допустимого диапазона"""
        bp_answer = Answer.objects.create(
            text="Свой вариант",
            question=self.bp_question
        )
        url = reverse('questionnaire_view', args=[self.bp_question.order])

        # Значения вне диапазона
        response = self.client.post(url, {
            'answers': [bp_answer.id],
            'free_text': '300/200'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Проверьте корректность значений (допустимый диапазон: 50-250/30-150)")

    def test_free_text_with_multiple_options_error(self):
        """Проверка ошибки при выборе нескольких вариантов со свободным текстом"""
        # Создаем вопрос с разрешенным свободным текстом
        question = Question.objects.create(
            text="Test question",
            order=5,
            allow_free_text=True
        )

        # Создаем обычные ответы и ответ для свободного текста
        regular_answer = Answer.objects.create(text="Regular Option", question=question)
        free_text_answer = Answer.objects.create(text="Свой вариант", question=question)

        url = reverse('questionnaire_view', args=[question.order])

        # Пытаемся отправить оба типа ответов
        response = self.client.post(url, {
            'answers': [regular_answer.id, free_text_answer.id],
            'free_text': 'Мой вариант'
        })

        # Проверяем ошибку
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Нельзя выбирать другие варианты вместе с &#x27;Свой вариант&#x27;"
        )

        # Проверяем, что ответ не сохранился
        self.assertFalse(
            UserResponse.objects.filter(
                user_profile=self.profile,
                question=question
            ).exists()
        )

    def test_single_choice_with_multiple_answers_error(self):
        """Проверка ошибки при выборе нескольких ответов в вопросе с единственным выбором"""
        # Создаем вопрос с единственным выбором
        single_choice_question = Question.objects.create(
            text="Single Choice Question",
            order=5,
            is_required=True,
            is_multiple_choice=False
        )

        # Создаем два ответа
        answer1 = Answer.objects.create(text="Option 1", question=single_choice_question)
        answer2 = Answer.objects.create(text="Option 2", question=single_choice_question)

        url = reverse('questionnaire_view', args=[single_choice_question.order])

        # Пытаемся отправить два ответа
        response = self.client.post(url, {
            'answers': [answer1.id, answer2.id]
        })

        # Проверяем ошибку
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Выберите только один вариант")

        # Проверяем, что ответ не сохранился
        self.assertFalse(
            UserResponse.objects.filter(
                user_profile=self.profile,
                question=single_choice_question
            ).exists()
        )
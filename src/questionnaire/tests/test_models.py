from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from questionnaire.models import Question, Answer, AnonymousUserProfile, UserResponse


class QuestionModelTest(TransactionTestCase):
    def test_create_question(self):
        q = Question.objects.create(
            text="Test question",
            order=1,
            description="Test description"
        )
        self.assertEqual(q.text, "Test question")
        self.assertEqual(q.order, 1)

    def test_question_validation(self):
        # Проверка валидации для вопросов с числовым ответом
        with self.assertRaises(ValidationError):
            q = Question(
                text="Invalid question",
                is_numeric_input=True,
                allow_free_text=True
            )
            q.full_clean()

    def test_auto_order_assignment(self):
        q1 = Question.objects.create(text="Q1")
        q2 = Question.objects.create(text="Q2")
        self.assertEqual(q1.order, 1)
        self.assertEqual(q2.order, 2)

    def test_free_text_with_multiple_choice_validation(self):
        """Проверка несовместимости свободного текста с множественным выбором"""
        with self.assertRaises(ValidationError) as context:
            q = Question(
                text="Invalid combo",
                allow_free_text=True,
                is_multiple_choice=True
            )
            q.full_clean()
        self.assertIn("Свободный ответ не может быть разрешен", str(context.exception))

    def test_numeric_with_multiple_choice_validation(self):
        """Проверка несовместимости числового ответа с множественным выбором"""
        with self.assertRaises(ValidationError) as context:
            q = Question(
                text="Invalid numeric",
                is_numeric_input=True,
                is_multiple_choice=True
            )
            q.full_clean()
        self.assertIn("Числовой ответ несовместим с множественным выбором", str(context.exception))

    def test_numeric_with_existing_answers_validation(self):
        """Проверка числового вопроса с существующими ответами"""
        q = Question.objects.create(
            text="Parent question",
            order=1
        )
        Answer.objects.create(text="Answer 1", question=q)

        q.is_numeric_input = True
        with self.assertRaises(ValidationError) as context:
            q.full_clean()
        self.assertIn("Числовой вопрос не должен иметь вариантов ответов", str(context.exception))

    def test_auto_order_zero_assignment(self):
        """Автоназначение порядка при order=0"""
        q = Question.objects.create(text="Auto-order test")
        self.assertEqual(q.order, 1)  # Первый вопрос получает порядок=1

        q2 = Question.objects.create(text="Auto-order test 2")
        self.assertEqual(q2.order, 2)

    def test_duplicate_order_validation(self):
        """Проверка уникальности порядка"""
        # Создаем первый вопрос
        Question.objects.create(text="Q1", order=10)

        # Пытаемся создать второй вопрос с таким же порядком
        q2 = Question(text="Q2", order=10)

        with self.assertRaises(ValidationError) as context:
            q2.full_clean()

        # Проверяем что ошибка содержит нужное сообщение
        self.assertIn('order', context.exception.message_dict)
        self.assertIn(
            'Порядок должен быть уникальным',
            str(context.exception.message_dict['order'])
        )

    def test_auto_order_empty_database(self):
        """Автоназначение порядка при пустой базе данных"""
        # Удаляем все вопросы
        Question.objects.all().delete()

        # Создаем первый вопрос
        q = Question.objects.create(text="First question")
        self.assertEqual(q.order, 1)

        # Создаем второй вопрос
        q2 = Question.objects.create(text="Second question")
        self.assertEqual(q2.order, 2)

    def test_auto_order_non_empty_database(self):
        """Автоназначение порядка в непустой базе"""
        # Удаляем все вопросы
        Question.objects.all().delete()

        # Создаем вопрос с высоким порядком
        q_high = Question.objects.create(text="High order", order=100)

        # Создаем вопрос без указания порядка
        q_auto = Question.objects.create(text="Auto order")

        # Проверяем что порядок назначен правильно
        self.assertEqual(q_auto.order, 101)

    def test_auto_order_with_existing_questions(self):
        """Автоназначение порядка при существующих вопросах"""
        # Удаляем все вопросы
        Question.objects.all().delete()

        # Создаем несколько вопросов
        Question.objects.create(text="Q1", order=1)
        Question.objects.create(text="Q2", order=2)
        Question.objects.create(text="Q3", order=3)

        # Создаем вопрос без указания порядка
        q_auto = Question.objects.create(text="Auto order")

        # Проверяем что порядок назначен правильно
        self.assertEqual(q_auto.order, 4)

    def test_clean_auto_order_assignment(self):
        """Проверка автоматического назначения порядка в методе clean()"""
        # Пустая база - порядок должен стать 1
        q = Question(text="Test clean order")
        q.full_clean()  # Явный вызов валидации
        self.assertEqual(q.order, 1)

        # Существующие вопросы - порядок должен стать max+1
        Question.objects.create(text="Q1", order=5)
        Question.objects.create(text="Q2", order=10)

        q = Question(text="Test clean order non-empty")
        q.full_clean()
        self.assertEqual(q.order, 11)

    def test_clean_duplicate_order(self):
        """Проверка валидации дубликатов порядка в методе clean()"""
        Question.objects.create(text="Q1", order=5)

        # Попытка создать вопрос с существующим порядком
        q = Question(text="Q-conflict", order=5)
        with self.assertRaises(ValidationError) as context:
            q.full_clean()  # Должен вызвать ошибку валидации

        self.assertIn('order', context.exception.message_dict)
        self.assertIn(
            'Порядок должен быть уникальным',
            str(context.exception.message_dict['order'])
        )

    def test_question_str(self):
        """Проверка строкового представления вопроса"""
        q = Question.objects.create(text="Test question")
        self.assertEqual(str(q), "Test question")


class AnswerModelTest(TransactionTestCase):
    def setUp(self):
        self.question = Question.objects.create(text="Parent question")

    def test_create_answer(self):
        a = Answer.objects.create(
            text="Test answer",
            question=self.question,
            value=0.5
        )
        self.assertEqual(a.text, "Test answer")
        self.assertEqual(a.value, 0.5)

    def test_answer_str(self):
        """Проверка строкового представления ответа"""
        question = Question.objects.create(text="Test question")
        answer = Answer.objects.create(
            text="Test answer text",
            question=question
        )
        self.assertEqual(str(answer), "Test answer text")

    def test_free_text_signal_updates_answers(self):
        """Сигнал помечает ответы как опциональные при allow_free_text"""
        q = Question.objects.create(
            text="Parent question for signal",
            allow_free_text=False
        )
        a1 = Answer.objects.create(text="Answer 1", question=q)
        a2 = Answer.objects.create(text="Answer 2", question=q)

        # Активируем свободный текст
        q.allow_free_text = True
        q.save()

        # Перезагружаем ответы
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertTrue(a1.is_optional)
        self.assertTrue(a2.is_optional)

class UserProfileModelTest(TransactionTestCase):
    def test_create_profile(self):
        profile = AnonymousUserProfile.objects.create(
            session_key="test_session",
            gender='M',
            age=30
        )
        self.assertEqual(profile.gender, 'M')
        self.assertEqual(profile.age, 30)

    def test_profile_str(self):
        """Проверка строкового представления профиля"""
        profile = AnonymousUserProfile(session_key="test-session-key")
        self.assertIn("test-session-key", str(profile))

class UserResponseModelTest(TransactionTestCase):
    def setUp(self):
        self.profile = AnonymousUserProfile.objects.create(
            session_key="test_session"
        )
        self.question = Question.objects.create(
            text="Response question",
            order=1
        )
        self.answer = Answer.objects.create(
            text="Test answer",
            question=self.question,
            value=1.0
        )

    def test_create_response(self):
        response = UserResponse.objects.create(
            user_profile=self.profile,
            question=self.question
        )
        response.selected_answers.add(self.answer)
        self.assertEqual(response.selected_answers.count(), 1)
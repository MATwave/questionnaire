import re
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Question, Answer, UserResponse, AnonymousUserProfile
from .utils import calculate_user_rating


def user_profile_view(request):
    """
    Обработка профиля пользователя:
    - Создание сессии при необходимости
    - Заполнение анкетных данных
    - Перенаправление на следующую страницу
    """
    # Инициализация сессии
    if not request.session.session_key:
        request.session.create()

    # Получение или создание профиля
    profile, created = AnonymousUserProfile.objects.get_or_create(
        session_key=request.session.session_key
    )

    # Проверка завершенности опроса
    if profile.filled_survey:
        return redirect('thank_you_view')

    # Проверка полноты профиля
    if all([profile.gender, profile.age, profile.height, profile.weight]):
        return redirect('questionnaire_start')

    # Обработка POST-запроса (сохранение данных профиля)
    if request.method == 'POST':
        return _handle_profile_post(request, profile)

    return render(request, 'user_profile_form.html', {'profile': profile})


def _handle_profile_post(request, profile):
    """Обрабатывает отправку формы профиля"""
    profile.gender = request.POST.get('gender')
    profile.age = request.POST.get('age')
    profile.height = request.POST.get('height')
    profile.weight = request.POST.get('weight')
    profile.save()
    return redirect('questionnaire_start')


def questionnaire_view(request, question_order=None):
    """
    Основной обработчик вопросов анкеты:
    - Проверяет сессию и профиль
    - Рассчитывает прогресс
    - Обрабатывает ответы
    - Управляет навигацией между вопросами
    """
    # Валидация сессии и профиля
    session_key = _validate_session(request)
    if not session_key:
        return redirect('user_profile_view')

    profile = get_object_or_404(AnonymousUserProfile, session_key=session_key)

    if profile.filled_survey:
        return redirect('thank_you_view')

    # Получение вопросов и расчет прогресса
    questions = Question.objects.all().order_by('order')
    question_count = questions.count()

    if not questions.exists():
        return redirect('thank_you_view')

    progress, answered = _calculate_progress(profile, question_count)

    # Обработка текущего вопроса
    question = _get_current_question(question_order, questions)
    if not question:
        return HttpResponseRedirect(reverse('questionnaire_view', args=[questions.first().order]))

    # Обработка ответа
    if request.method == 'POST':
        return _handle_question_post(request, profile, question, progress, answered, question_count)

    # GET-запрос: отображение вопроса
    return render(request, 'questionnaire.html', {
        'question': question,
        'progress': progress,
        'answered_questions': answered,
        'question_count': question_count,
        'next_question_exists': question.order < question_count
    })


def _validate_session(request):
    """Проверяет наличие действительной сессии"""
    if not request.session.session_key:
        request.session.create()
        return None
    return request.session.session_key


def _calculate_progress(profile, question_count):
    """Рассчитывает прогресс заполнения анкеты"""
    answered = UserResponse.objects.filter(
        user_profile=profile
    ).values('question').distinct().count()

    progress = int((answered / question_count) * 100) if question_count else 0
    return progress, answered


def _get_current_question(question_order, questions):
    """Получает текущий вопрос по порядковому номеру"""
    """Получает текущий вопрос по порядковому номеру"""
    if question_order:
        try:
            # Защита от некорректных значений
            order = int(question_order)
            return Question.objects.get(order=order)
        except (Question.DoesNotExist, ValueError):
            return None
    return None


def _handle_question_post(request, profile, question, progress, answered, question_count):
    """Обрабатывает отправку ответа на вопрос"""
    # Извлечение данных из POST-запроса
    selected_ids = request.POST.getlist('answers')
    free_text = request.POST.get('free_text', '').strip() if question.allow_free_text else ""
    numeric = request.POST.get('numeric_answer', '').strip() if question.is_numeric_input else None

    # Валидация ответа
    error = _validate_response(question, selected_ids, free_text, numeric)

    if error:
        return _render_question_error(
            request, question, progress, answered, question_count,
            selected_ids, free_text, numeric, error
        )

    # Сохранение ответа
    _save_user_response(profile, question, selected_ids, free_text, numeric)

    # Определение следующего вопроса
    next_question = _determine_next_question(question, selected_ids, free_text, numeric)

    # Перенаправление или завершение опроса
    if next_question:
        return HttpResponseRedirect(reverse('questionnaire_view', args=[next_question.order]))
    else:
        profile.filled_survey = True
        profile.save()
        return redirect('thank_you_view')


def _validate_response(question, selected_ids, free_text, numeric):
    """Валидирует ответ пользователя с учетом типа вопроса"""
    # TODO: Вынести специфичные проверки (холестерин, давление) в отдельные валидаторы
    error = None

    # Числовой ввод
    if question.is_numeric_input:
        error = _validate_numeric_input(question, numeric)

    # Артериальное давление (специальная обработка)
    elif question.description == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ":
        error = _validate_blood_pressure(free_text, question)

    # Остальные типы вопросов
    else:
        error = _validate_general_question(question, selected_ids, free_text)

    return error


def _validate_numeric_input(question, numeric):
    """Валидация для числовых вопросов"""
    if not numeric and question.is_required:
        return "Введите числовое значение"

    if not numeric:
        return None

    try:
        numeric_value = float(numeric)

        # Специфичная проверка для холестерина
        if question.description == "ОБЩИЙ ХОЛЕСТЕРИН":
            if numeric_value > 0 and not (2.0 <= numeric_value <= 30.0):
                return "Проверьте значение (допустимо 2.0-30.0 ммоль/л)"

        # Общая проверка для отрицательных значений
        elif numeric_value < 0:
            return "Значение не может быть отрицательным"

    except ValueError:
        return "Введите корректное число"

    return None


def _validate_blood_pressure(free_text, question):
    """Специальная валидация для артериального давления"""
    # TODO: Вынести регулярное выражение и диапазоны в константы

    # Проверка обязательности вопроса
    if question.is_required and not free_text.strip():
        return "Введите значение артериального давления или укажите 'не знаю'"

    # Обработка варианта "не знаю"
    if free_text.lower() in ['не знаю', 'неизвестно']:
        return None

    # Проверка формата
    if not re.match(r'^\d+/\d+$', free_text):
        return "Введите давление в формате ЧИСЛО/ЧИСЛО (например: 120/80) или введите 'не знаю'"

    try:
        systolic, diastolic = map(int, free_text.split('/'))
        if not (50 <= systolic <= 250) or not (30 <= diastolic <= 150):
            return "Проверьте корректность значений (допустимый диапазон: 50-250/30-150)"
    except ValueError:
        return "Некорректные значения давления"

    return None


def _validate_general_question(question, selected_ids, free_text):
    """Валидация для общих вопросов"""
    # Удаляем 'free_text' из списка выбранных ответов для валидации
    clean_ids = [aid for aid in selected_ids if aid != 'free_text']
    has_free_text = question.allow_free_text and bool(free_text) and 'free_text' in selected_ids

    selected_answers = Answer.objects.filter(id__in=clean_ids)

    # Проверка комбинации "Свой вариант" + другие ответы
    if has_free_text and len(clean_ids) > 0:
        return "Нельзя выбирать другие варианты вместе с 'Свой вариант'"

    # Проверка обязательности вопроса
    if question.is_required:
        min_answers = 1 if question.is_multiple_choice else 0

        if not selected_answers.exists() and not has_free_text:
            error_msg = "Выберите вариант"
            if question.allow_free_text:
                error_msg += " или заполните поле"
            return error_msg

        if not question.is_multiple_choice and len(clean_ids) > 1:
            return "Выберите только один вариант"

    return None


def _render_question_error(request, question, progress, answered, question_count, selected_ids, free_text, numeric,
                           error):
    """Рендерит страницу вопроса с ошибкой валидации"""
    # TODO: Оптимизировать запрос selected_answers
    try:
        selected_answers = Answer.objects.filter(id__in=selected_ids)
    except (ValueError, TypeError):
        selected_answers = []

    return render(request, 'questionnaire.html', {
        'question': question,
        'progress': progress,
        'answered_questions': answered,
        'question_count': question_count,
        'error': error,
        'user_response': {
            'selected_answers': selected_answers,
            'free_text_answer': free_text,
            'numeric_answer': numeric
        }
    })


def _save_user_response(profile, question, selected_ids, free_text, numeric):
    """Сохраняет ответ пользователя в базу данных"""
    # Фильтруем 'free_text' перед сохранением
    valid_ids = [aid for aid in selected_ids if aid != 'free_text' and aid.isdigit()]

    response, _ = UserResponse.objects.update_or_create(
        user_profile=profile,
        question=question,
        defaults={
            'free_text_answer': free_text if question.allow_free_text else '',
            'numeric_answer': float(numeric) if question.is_numeric_input and numeric else None
        }
    )

    if not question.is_numeric_input:
        response.selected_answers.set(valid_ids)


def _determine_next_question(question, selected_ids, free_text, numeric):
    """Определяет следующий вопрос на основе ответа"""
    # TODO: Рефакторинг логики определения следующего вопроса
    if question.is_numeric_input or (question.allow_free_text and free_text):
        return Question.objects.filter(order__gt=question.order).first()

    if selected_ids:
        first_answer = Answer.objects.filter(id__in=selected_ids).first()
        return first_answer.next_question or Question.objects.filter(
            order__gt=question.order
        ).first()

    return None


def thank_you_view(request):
    """Страница благодарности после завершения опроса"""
    # Проверка сессии
    if not request.session.session_key:
        return redirect('home')

    # Получение профиля
    profile = get_object_or_404(
        AnonymousUserProfile,
        session_key=request.session.session_key
    )

    # Проверка завершенности опроса
    if not profile.filled_survey:
        return redirect('questionnaire_start')

    # Расчет и отображение рейтинга
    rating_data = calculate_user_rating(profile)
    return render(request, 'thank_you.html', rating_data)


def home_view(request):
    """Домашняя страница"""
    return render(request, 'home.html')
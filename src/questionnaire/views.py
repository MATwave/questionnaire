import re

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import Question, Answer, UserResponse, AnonymousUserProfile
from .utils import calculate_user_rating


def user_profile_view(request):
    # Session handling
    if not request.session.session_key:
        request.session.create()

    # Profile handling
    profile, created = AnonymousUserProfile.objects.get_or_create(
        session_key=request.session.session_key
    )

    if profile.filled_survey:
        return redirect('thank_you_view')

    # Check if profile is complete
    if all([profile.gender, profile.age, profile.height, profile.weight]):
        return redirect('questionnaire_start')

    # Profile form processing
    if request.method == 'POST':
        profile.gender = request.POST.get('gender')
        profile.age = request.POST.get('age')
        profile.height = request.POST.get('height')
        profile.weight = request.POST.get('weight')
        profile.save()
        return redirect('questionnaire_start')

    return render(request, 'user_profile_form.html', {'profile': profile})


def questionnaire_view(request, question_order=None):
    # Session and profile validation
    if not request.session.session_key:
        return redirect('user_profile_view')

    profile = get_object_or_404(AnonymousUserProfile, session_key=request.session.session_key)

    if profile.filled_survey:
        return redirect('thank_you_view')

    # Questions setup
    questions = Question.objects.all().order_by('order')
    question_count = questions.count()

    if not questions.exists():
        return redirect('thank_you_view')

    # Progress calculation
    answered = UserResponse.objects.filter(user_profile=profile).values('question').distinct().count()
    progress = int((answered / question_count) * 100) if question_count else 0

    # Current question handling
    if question_order:
        question = get_object_or_404(Question, order=question_order)
    else:
        return HttpResponseRedirect(reverse('questionnaire_view', args=[questions.first().order]))

    # Answer processing
    if request.method == 'POST':
        error = None
        selected_ids = request.POST.getlist('answers')
        free_text = request.POST.get('free_text', '').strip() if question.allow_free_text else ""
        numeric = request.POST.get('numeric_answer', '').strip() if question.is_numeric_input else None
        selected_answers = Answer.objects.none()
        has_free_text = question.allow_free_text and bool(free_text)

        # Validation logic
        if question.is_numeric_input:
            if not numeric:
                if question.is_required:
                    error = "Введите числовое значение"
            else:
                try:
                    numeric = float(numeric)
                    # Специфичная валидация для холестерина
                    if question.description == "ОБЩИЙ ХОЛЕСТЕРИН":
                        if numeric < 2.0 or numeric > 15.0:
                            error = "Проверьте корректность значения (допустимый диапазон: 2.0-15.0 ммоль/л)"
                        else:
                            error = None
                    else:
                        # Общая валидация для других числовых вопросов
                        error = "Значение не может быть отрицательным" if numeric < 0 else None
                except ValueError:
                    error = "Введите корректное число"
        else:
            # Новая логика валидации для артериального давления
            if question.description == "АРТЕРИАЛЬНОЕ ДАВЛЕНИЕ":
                if has_free_text:
                    if free_text.lower() in ['не знаю', 'неизвестно']:
                        # Корректная обработка "не знаю"
                        pass
                    else:
                        # Проверка формата
                        if not re.match(r'^\d+/\d+$', free_text):
                            error = "Введите давление в формате ЧИСЛО/ЧИСЛО (например: 120/80) или введите 'не знаю'"
                        else:
                            try:
                                systolic, diastolic = map(int, free_text.split('/'))
                                if not (50 <= systolic <= 250) or not (30 <= diastolic <= 150):
                                    error = "Проверьте корректность значений (допустимый диапазон: 50-250/30-150)"
                            except ValueError:
                                error = "Некорректные значения давления"
                elif question.is_required:
                    error = "Введите значение артериального давления или укажите 'не знаю'"

            # Общая валидация для остальных вопросов
            else:
                if has_free_text:
                    if len(selected_ids) > 1:
                        error = "Нельзя выбирать другие варианты вместе с 'Свой вариант'"
                    elif not question.allow_free_text or not free_text:
                        error = "Укажите ваш вариант ответа" if not free_text else "Свободный ответ не разрешен"
                else:
                    selected_answers = Answer.objects.filter(id__in=selected_ids)
                    if free_text:
                        error = "Уберите текст или выберите 'Свой вариант'"

                # Required field check
                if question.is_required and not error:
                    min_answers = 1 if question.is_multiple_choice else 0
                    if not selected_answers.exists() and not (has_free_text and free_text):
                        error = "Выберите вариант" + (" или заполните поле" if question.allow_free_text else "")
                    elif not question.is_multiple_choice and len(selected_ids) > 1:
                        error = "Выберите только один вариант"

        # Handle validation errors
        if error:
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

        # Save response
        response, _ = UserResponse.objects.update_or_create(
            user_profile=profile,
            question=question,
            defaults={
                'free_text_answer': free_text if has_free_text else '',
                'numeric_answer': numeric if question.is_numeric_input else None
            }
        )
        if not question.is_numeric_input:
            response.selected_answers.set(selected_answers)

        # Determine next question
        next_question = None
        if question.is_numeric_input or has_free_text:
            next_question = Question.objects.filter(order__gt=question.order).first()
        elif selected_answers.exists():
            next_question = selected_answers.first().next_question or Question.objects.filter(
                order__gt=question.order
            ).first()

        # Final redirects
        if next_question:
            return HttpResponseRedirect(reverse('questionnaire_view', args=[next_question.order]))
        else:
            profile.filled_survey = True
            profile.save()
            return redirect('thank_you_view')

    # GET request handling
    return render(request, 'questionnaire.html', {
        'question': question,
        'progress': progress,
        'answered_questions': answered,
        'question_count': question_count,
        'next_question_exists': question.order < question_count
    })


def thank_you_view(request):
    if not request.session.session_key:
        return redirect('home')

    profile = get_object_or_404(AnonymousUserProfile, session_key=request.session.session_key)

    if not profile.filled_survey:
        return redirect('questionnaire_start')

    return render(request, 'thank_you.html', calculate_user_rating(profile))


def home_view(request):
    return render(request, 'home.html')
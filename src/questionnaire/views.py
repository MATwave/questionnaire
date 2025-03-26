from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import Question, Answer, UserResponse, AnonymousUserProfile


def user_profile_view(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    user_profile, created = AnonymousUserProfile.objects.get_or_create(session_key=session_key)

    if user_profile.filled_survey:
        return redirect('thank_you_view')

    if user_profile.gender and user_profile.age and user_profile.height and user_profile.weight:
        # Изменено здесь: используем имя маршрута для старта опроса
        return redirect('questionnaire_start')  # <--- Исправлено

    if request.method == 'POST':
        user_profile.gender = request.POST.get('gender')
        user_profile.age = request.POST.get('age')
        user_profile.height = request.POST.get('height')
        user_profile.weight = request.POST.get('weight')
        user_profile.save()
        # Изменено здесь: используем правильный маршрут
        return redirect('questionnaire_start')  # <--- Исправлено

    return render(request, 'user_profile_form.html', {'profile': user_profile})


def questionnaire_view(request, question_order=None):
    session_key = request.session.session_key
    if not session_key:
        return redirect('user_profile_view')

    user_profile = get_object_or_404(AnonymousUserProfile, session_key=session_key)

    if user_profile.filled_survey:
        return redirect('thank_you_view')

    all_questions = Question.objects.all().order_by('order')
    total_questions = all_questions.count()

    if not all_questions.exists() or total_questions == 0:
        return redirect('thank_you_view')

    answered_questions = UserResponse.objects.filter(user_profile=user_profile).values('question').distinct().count()
    progress = int((answered_questions / total_questions) * 100) if total_questions > 0 else 0

    if question_order:
        question = get_object_or_404(Question, order=question_order)
    else:
        first_question = all_questions.first()
        return HttpResponseRedirect(reverse('questionnaire_view', args=[first_question.order]))

    if request.method == 'POST':
        selected_answers_ids = request.POST.getlist('answers')
        free_text_answer = request.POST.get('free_text', '').strip() if question.allow_free_text else ""
        error = None
        has_free_text = 'free_text' in selected_answers_ids
        selected_answers = Answer.objects.none()

        # Валидация выбора free_text
        if has_free_text:
            if len(selected_answers_ids) > 1:
                error = "Нельзя выбирать другие варианты вместе с 'Другой вариант'"
            elif not question.allow_free_text:
                error = "Свободный ответ не разрешен для этого вопроса"
            elif not free_text_answer:
                error = "Укажите ваш вариант ответа"
        else:
            # Обрабатываем обычные ответы
            selected_answers = Answer.objects.filter(id__in=selected_answers_ids)
            if free_text_answer:
                error = "Уберите текст или выберите 'Другой вариант'"

        # Общая валидация обязательности
        if question.is_required and not error:
            if question.is_multiple_choice:
                if not selected_answers.exists() and not (has_free_text and free_text_answer):
                    error = "Выберите хотя бы один вариант" + (
                        " или заполните поле" if question.allow_free_text else "")
            else:
                if len(selected_answers_ids) > 1:
                    error = "Выберите только один вариант"
                elif not selected_answers.exists() and not (has_free_text and free_text_answer):
                    error = "Выберите вариант" + (" или заполните поле" if question.allow_free_text else "")

        if error:
            return render(request, 'questionnaire.html', {
                'question': question,
                'progress': progress,
                'answered_questions': answered_questions,
                'question_count': total_questions,
                'error': error,
                'user_response': {
                    'selected_answers': selected_answers,
                    'free_text_answer': free_text_answer
                }
            })

        # Сохранение ответа
        response, created = UserResponse.objects.update_or_create(
            user_profile=user_profile,
            question=question,
            defaults={'free_text_answer': free_text_answer if has_free_text else ''}
        )
        response.selected_answers.set(selected_answers)

        # Определение следующего вопроса
        next_question = None
        if has_free_text:
            # Для свободного ответа ищем следующий вопрос по порядку
            next_question = Question.objects.filter(order__gt=question.order).order_by('order').first()
        elif selected_answers.exists():
            # Логика определения следующего вопроса через ответы
            first_answer = selected_answers.first()
            next_question = first_answer.next_question or Question.objects.filter(
                order__gt=question.order
            ).order_by('order').first()

        if not next_question:
            next_question = Question.objects.filter(order__gt=question.order).order_by('order').first()

        if next_question:
            return HttpResponseRedirect(reverse('questionnaire_view', args=[next_question.order]))
        else:
            user_profile.filled_survey = True
            user_profile.save()
            return redirect('thank_you_view')

    return render(request, 'questionnaire.html', {
        'question': question,
        'progress': progress,
        'answered_questions': answered_questions,
        'question_count': total_questions
    })

def thank_you_view(request):
    return render(request, 'thank_you.html')

def home_view(request):
    return render(request, 'home.html')
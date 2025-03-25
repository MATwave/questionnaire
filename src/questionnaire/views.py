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
        # Изменено: получаем список выбранных ответов
        selected_answers_ids = request.POST.getlist('answers')
        free_text_answer = request.POST.get('free_text', '').strip() if question.allow_free_text else ""

        # Изменено: получаем все выбранные ответы
        selected_answers = Answer.objects.filter(id__in=selected_answers_ids)
        error = None

        if question.is_required:
            # Валидация для множественного выбора
            if question.is_multiple_choice:
                if not selected_answers and not free_text_answer:
                    error = "Выберите хотя бы один вариант ответа" + \
                            (" или заполните поле" if question.allow_free_text else "")
            else:
                # Валидация для одиночного выбора
                if len(selected_answers) > 1:
                    error = "Выберите только один вариант ответа"
                elif not selected_answers and not free_text_answer:
                    error = "Выберите вариант ответа" + \
                            (" или заполните поле" if question.allow_free_text else "")

            if error:
                return render(request, 'questionnaire.html', {
                    'question': question,
                    'progress': progress,
                    'answered_questions': answered_questions,
                    'question_count': total_questions,
                    'error': error
                })

        # Изменено: сохраняем несколько ответов
        response, created = UserResponse.objects.update_or_create(
            user_profile=user_profile,
            question=question,
            defaults={'free_text_answer': free_text_answer}
        )
        response.selected_answers.set(selected_answers)

        # Определение следующего вопроса (первого из выбранных ответов)
        next_question = None
        if selected_answers.exists():
            first_answer = selected_answers.first()
            if first_answer.next_question:
                next_question = first_answer.next_question

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
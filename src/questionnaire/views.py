from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Questionnaire, Question, Answer, UserResponse, AnonymousUserProfile


def questionnaire_list(request):
    questionnaires = Questionnaire.objects.all()
    return render(request, 'questionnaire_list.html', {'questionnaires': questionnaires})


def user_profile_view(request, questionnaire_id):
    # Получаем текущий идентификатор сессии
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Получаем профиль пользователя для текущей сессии
    user_profile, created = AnonymousUserProfile.objects.get_or_create(session_key=session_key)

    if user_profile.gender and user_profile.age and user_profile.height and user_profile.weight:
        # Если данные собраны, начинаем опрос
        return redirect('questionnaire_view', questionnaire_id=questionnaire_id)

    if request.method == 'POST':
        user_profile.gender = request.POST.get('gender')
        user_profile.age = request.POST.get('age')
        user_profile.height = request.POST.get('height')
        user_profile.weight = request.POST.get('weight')
        user_profile.save()
        return redirect('questionnaire_view', questionnaire_id=questionnaire_id)

    return render(request, 'user_profile_form.html', {'profile': user_profile})

def questionnaire_view(request, questionnaire_id, question=None):
    session_key = request.session.session_key
    if not session_key:
        return redirect('user_profile_view', questionnaire_id=questionnaire_id)

    questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id)
    responses = UserResponse.objects.filter(session_key=session_key, questionnaire_id=questionnaire_id)
    question_count = questionnaire.questions.count()
    answered_questions = responses.values('question').distinct().count()

    if answered_questions == question_count:
        return redirect('thank_you_view')

    if question:
        question = get_object_or_404(Question, id=question)
    else:
        question = questionnaire.questions.first()

    progress = int((answered_questions / question_count) * 100)

    if request.method == 'POST':
        selected_answer_id = request.POST.get('answer')
        free_text_answer = request.POST.get('free_text', '').strip() if question.allow_free_text else ""

        selected_answer = Answer.objects.filter(id=selected_answer_id).first() if selected_answer_id else None

        if question.allow_free_text and not selected_answer and not free_text_answer:
            return render(request, 'questionnaire.html', {
                'questionnaire': questionnaire,
                'question': question,
                'progress': progress,
                'answered_questions': answered_questions,
                'question_count': question_count,
                'error': 'Пожалуйста, выберите вариант ответа или заполните поле свободного ответа.'
            })

        # Обновляем или создаем ответ
        UserResponse.objects.update_or_create(
            session_key=session_key,
            questionnaire=questionnaire,
            question=question,
            defaults={
                'selected_answer': selected_answer,
                'free_text_answer': free_text_answer
            }
        )

        if selected_answer and selected_answer.next_question:
            next_question = selected_answer.next_question
        else:
            next_question = questionnaire.questions.filter(id__gt=question.id).first()

        return redirect(reverse('questionnaire_view_with_question', kwargs={'questionnaire_id': questionnaire_id, 'question': next_question.id}) if next_question else 'thank_you_view')

    return render(request, 'questionnaire.html', {
        'questionnaire': questionnaire,
        'question': question,
        'progress': progress,
        'answered_questions': answered_questions,
        'question_count': question_count
    })

def thank_you_view(request):
    return render(request, 'thank_you.html')

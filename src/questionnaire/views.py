from django.shortcuts import render, redirect
from .models import Questionnaire, Question, Answer, UserResponse

def questionnaire_view(request, questionnaire_id):
    questionnaire = Questionnaire.objects.get(id=questionnaire_id)
    question_id = request.GET.get('question')
    question = Question.objects.get(id=question_id) if question_id else questionnaire.questions.first()

    if request.method == 'POST':
        selected_answer_id = request.POST.get('answer')
        free_text_answer = request.POST.get('free_text', '').strip() if question.allow_free_text else ""

        selected_answer = Answer.objects.get(id=selected_answer_id) if selected_answer_id else None

        UserResponse.objects.create(
            questionnaire=questionnaire,
            question=question,
            selected_answer=selected_answer,
            free_text_answer=free_text_answer
        )

        next_question = selected_answer.next_question if selected_answer else None

        if next_question:
            return redirect(f'?question={next_question.id}')
        else:
            return render(request, 'thank_you.html')

    return render(request, 'questionnaire.html', {'question': question})


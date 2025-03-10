from django.shortcuts import render, redirect
from .models import Questionnaire, Question, Answer

def questionnaire_view(request, questionnaire_id):
    questionnaire = Questionnaire.objects.get(id=questionnaire_id)
    question_id = request.GET.get('question')
    if question_id:
        question = Question.objects.get(id=question_id)
    else:
        question = questionnaire.questions.first()

    if request.method == 'POST':
        selected_answer_id = request.POST.get('answer')
        selected_answer = Answer.objects.get(id=selected_answer_id)
        next_question = selected_answer.next_question
        if next_question:
            return redirect(f'?question={next_question.id}')
        else:
            return redirect('thank_you')  # например, страница благодарности

    return render(request, 'questionnaire.html', {'question': question})

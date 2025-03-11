from django.db import models

class Questionnaire(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class Question(models.Model):
    text = models.CharField(max_length=500)
    questionnaire = models.ForeignKey(Questionnaire, related_name='questions', on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    allow_free_text = models.BooleanField(default=False)  # Разрешен ли свободный ответ

    def __str__(self):
        return self.text


class Answer(models.Model):
    text = models.CharField(max_length=300)
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    next_question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL)
    is_optional = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class UserResponse(models.Model):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.SET_NULL)
    free_text_answer = models.TextField(blank=True)

    def __str__(self):
        if self.selected_answer:
            return f"{self.question.text} → {self.selected_answer.text}"
        return f"{self.question.text} → {self.free_text_answer}"

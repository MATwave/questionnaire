from django.db import models

class Questionnaire(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class Question(models.Model):
    text = models.CharField(max_length=500)
    questionnaire = models.ForeignKey(Questionnaire, related_name='questions', on_delete=models.CASCADE)

    def __str__(self):
        return self.text

class Answer(models.Model):
    text = models.CharField(max_length=300)
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE, verbose_name='Вопрос')
    next_question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL, related_name='next_answers', verbose_name='Следующий вопрос')

    def __str__(self):
        return self.text


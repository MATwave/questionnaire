from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now


class Questionnaire(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    text = models.CharField(max_length=500)
    description = models.CharField(max_length=200, blank=True, help_text="Краткое описание вопроса")  # Краткое описание
    questionnaire = models.ForeignKey(Questionnaire, related_name='questions', on_delete=models.CASCADE)
    is_required = models.BooleanField(default=True)
    allow_free_text = models.BooleanField(default=False)  # Разрешен ли свободный ответ

    def __str__(self):
        return self.text

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

@receiver(post_save, sender=Question)
def update_answers(sender, instance, created, **kwargs):
    if instance.allow_free_text:
        for answer in instance.answers.all():
            answer.is_optional = True
            answer.save()


class Answer(models.Model):
    text = models.CharField(max_length=300)
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    next_question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL)
    is_optional = models.BooleanField(default=False)
    value = models.FloatField(null=True, blank=True, default=0)

    def __str__(self):
        return self.text



class AnonymousUserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    session_key = models.CharField(max_length=40, unique=True)  # Уникальный ключ сессии пользователя
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)  # Пол пользователя
    age = models.IntegerField(null=True, blank=True)  # Возраст пользователя, опциональное поле
    height = models.FloatField(null=True, blank=True)  # Рост пользователя, опциональное поле
    weight = models.FloatField(null=True, blank=True)  # Вес пользователя, опциональное поле
    filled_survey = models.BooleanField(default=False)  # Отметка о заполнении анкеты

    def __str__(self):
        return f"Профиль анонимного пользователя {self.session_key}"

    class Meta:
        verbose_name = 'Профиль анонимного пользователя'
        verbose_name_plural = 'Профили анонимных пользователей'


class UserResponse(models.Model):
    session_key = models.CharField(max_length=40, default='default_session_key')
    #user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, null=True, blank=True, on_delete=models.CASCADE)
    free_text_answer = models.TextField(blank=True)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"Ответ на вопрос {self.question} для анкеты {self.questionnaire} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

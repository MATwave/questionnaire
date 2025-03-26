from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now


class Question(models.Model):
    text = models.CharField(max_length=500)
    description = models.CharField(max_length=200, blank=True, help_text="Краткое описание вопроса")
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0,help_text="Порядок отображения вопроса")
    allow_free_text = models.BooleanField(default=False)  # Разрешен ли свободный ответ
    is_multiple_choice = models.BooleanField(default=False, verbose_name="Множественный выбор")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text

    def clean(self):
        if self.allow_free_text and self.is_multiple_choice:
            raise ValidationError("Свободный ответ не может быть разрешен для вопросов с множественным выбором")

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
    user_profile = models.ForeignKey( AnonymousUserProfile, related_name='responses', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answers = models.ManyToManyField(Answer, blank=True)
    free_text_answer = models.TextField(blank=True)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return (f"Ответ {self.user_profile} на вопрос {self.question} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})")
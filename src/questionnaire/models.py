from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now


class Question(models.Model):
    text = models.CharField(
        max_length=500,
        verbose_name='Текст вопроса'
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Описание',
        help_text="Краткое описание/категория вопроса"
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name='Обязательный вопрос'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок',
        help_text="Число для порядка отображения (меньшее = выше)",
        unique=True
    )
    allow_free_text = models.BooleanField(
        default=False,
        verbose_name='Разрешить свободный ответ'
    )
    is_multiple_choice = models.BooleanField(
        default=False,
        verbose_name='Множественный выбор'
    )

    is_numeric_input = models.BooleanField(
        default=False,
        verbose_name='Числовой ответ',
        help_text="Разрешить ввод числового значения вместо выбора ответов"
    )

    class Meta:
        ordering = ['order']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return self.text

    def clean(self):
        super().clean()

        if self.allow_free_text and self.is_multiple_choice:
            raise ValidationError("Свободный ответ не может быть разрешен для вопросов с множественным выбором")

        if self.is_numeric_input:
            if self.allow_free_text:
                raise ValidationError("Числовой ответ несовместим со свободным текстом")
            if self.is_multiple_choice:
                raise ValidationError("Числовой ответ несовместим с множественным выбором")
            # Проверяем только для существующих вопросов
            if self.pk and self.answers.exists():
                raise ValidationError("Числовой вопрос не должен иметь вариантов ответов")

        if self._state.adding:
            if self.order == 0:
                last_order = Question.objects.aggregate(models.Max('order'))['order__max'] or 0
                self.order = last_order + 1
            else:
                if Question.objects.filter(order=self.order).exists():
                    raise ValidationError(
                        {'order': 'Порядок должен быть уникальным. Существующий порядок: %(value)s',
                         'params': {'value': self.order}}
                    )

    def save(self, *args, **kwargs):
        # Автоматическое назначение порядка при создании
        if self._state.adding and self.order == 0:
            last_order = Question.objects.aggregate(models.Max('order'))['order__max'] or 0
            self.order = last_order + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['order']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        constraints = [
            models.UniqueConstraint(
                fields=['order'],
                name='unique_question_order'
            )
        ]


@receiver(post_save, sender=Question)
def update_answers(sender, instance, created, **kwargs):
    if instance.allow_free_text:
        for answer in instance.answers.all():
            answer.is_optional = True
            answer.save()


class Answer(models.Model):
    text = models.CharField(
        max_length=300,
        verbose_name='Вариант ответа'
    )
    question = models.ForeignKey(
        Question,
        related_name='answers',
        on_delete=models.CASCADE,
        verbose_name='Вопрос'
    )
    next_question = models.ForeignKey(
        Question,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Следующий вопрос'
    )
    is_optional = models.BooleanField(
        default=False,
        verbose_name='Опциональный ответ'
    )
    value = models.FloatField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Значение для расчета'
    )

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        ordering = ['id']

    def __str__(self):
        return self.text


class AnonymousUserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='Ключ сессии'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name='Пол'
    )
    age = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Возраст'
    )
    height = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Рост (см)'
    )
    weight = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Вес (кг)'
    )
    filled_survey = models.BooleanField(
        default=False,
        verbose_name='Анкета заполнена'
    )

    class Meta:
        verbose_name = 'Анонимный профиль'
        verbose_name_plural = 'Анонимные профили'
        ordering = ['-id']

    def __str__(self):
        return f"Анонимный пользователь ({self.session_key})"


class UserResponse(models.Model):
    user_profile = models.ForeignKey(
        AnonymousUserProfile,
        related_name='responses',
        on_delete=models.CASCADE,
        verbose_name='Профиль пользователя'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name='Вопрос'
    )
    selected_answers = models.ManyToManyField(
        Answer,
        blank=True,
        verbose_name='Выбранные ответы'
    )
    free_text_answer = models.TextField(
        blank=True,
        verbose_name='Свободный ответ'
    )
    created_at = models.DateTimeField(
        default=now,
        verbose_name='Дата ответа'
    )

    numeric_answer = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Числовой ответ'
    )

    class Meta:
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        ordering = ['created_at']

    def __str__(self):
        return (f"Ответ {self.user_profile.session_key} на вопрос "
                f"'{self.question.text[:30]}...' ({self.created_at:%Y-%m-%d %H:%M})")
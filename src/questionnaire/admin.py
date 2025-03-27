import csv
from collections import defaultdict

from django.contrib import admin
import nested_admin
from django.db.models import Prefetch
from django.http import HttpResponse

from .models import Question, Answer, UserResponse, AnonymousUserProfile
from .utils import get_question_categories, calculate_user_rating


@admin.action(description="Экспортировать ответы в CSV")
def export_responses_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="responses.csv"'

    writer = csv.writer(response, delimiter='\t')

    questions = Question.objects.order_by('order')

    headers = [
        'Отметка времени', 'Пол', 'Возраст', 'Рост (см)', 'Вес (кг)',
        *questions.values_list('text', flat=True),
        'МБФ', 'ФАиРД', 'СТП', 'Образ жизни', 'Питание',
        'Пищевое поведение', 'Продукты питания', 'Стресс',
        'ИТОГО', 'Оценка соответствия'
    ]
    writer.writerow(headers)

    # Фильтруем только профили с ответами
    user_profiles = AnonymousUserProfile.objects.filter(
        responses__isnull=False
    ).prefetch_related(
        Prefetch('responses', queryset=UserResponse.objects.prefetch_related('selected_answers'))
    ).distinct()

    for profile in user_profiles:
        # Пропускаем профили без ответов
        if not profile.responses.exists():
            continue

        rating_data = calculate_user_rating(profile)

        # Основные данные
        first_response = profile.responses.earliest('created_at')
        row = [
            first_response.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            profile.gender or '',
            profile.age or '',
            profile.height or '',
            profile.weight or '',
        ]

        # Ответы на вопросы
        question_responses = {r.question_id: r for r in profile.responses.all()}
        answers_row = []
        for q in questions:
            response_obj = question_responses.get(q.id)
            if response_obj:
                answers = ", ".join(a.text for a in response_obj.selected_answers.all())
            else:
                answers = "Нет ответа"
            answers_row.append(answers)

        row += answers_row

        # Специальные колонки
        special_columns = [
            '', '',  # МБФ, ФАиРД
            rating_data.get('work_assessment_avg', 0),  # СТП
            '',  # Образ жизни
            rating_data.get('nutrition_avg', 0),  # Питание
            rating_data.get('eating_behavior_avg', 0),  # Пищевое поведение
            '',  # Продукты питания
            rating_data.get('stress_avg', 0),  # Стресс
            rating_data.get('total_score', 0),  # ИТОГО
            rating_data.get('rating', 'Нет оценки')  # Оценка соответствия
        ]

        writer.writerow(row + special_columns)

    return response


class AnswerInline(nested_admin.NestedStackedInline):
    model = Answer
    extra = 0
    fields = ['text', 'value', 'is_optional', 'next_question']
    fk_name = 'question'
    classes = ['collapse']
    verbose_name = 'Ответ'
    verbose_name_plural = 'Ответы'


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    list_display = ['text', 'order', 'is_required']
    list_display_links = ['text']
    inlines = [AnswerInline]
    ordering = ['order']
    actions = [export_responses_csv]
    save_on_top = True
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('text', 'description', 'order')
        }),
        ('Настройки', {
            'fields': ('is_required', 'allow_free_text', 'is_multiple_choice'),
            'classes': ('collapse',),
        }),
    )

    verbose_name = 'Вопрос'
    verbose_name_plural = 'Вопросы'


@admin.register(AnonymousUserProfile)
class AnonymousUserProfileAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'gender', 'age', 'height', 'weight', 'filled_survey']
    list_filter = ('gender', 'filled_survey')
    search_fields = ('session_key',)
    readonly_fields = ('session_key',)
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('session_key', 'gender', 'age', 'height', 'weight')
        }),
        ('Статус', {
            'fields': ('filled_survey',),
            'classes': ('collapse',),
        }),
    )

    verbose_name = 'Анонимный профиль'
    verbose_name_plural = 'Анонимные профили'


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = (
        'user_profile',
        'created_at',
        'question',
        'get_answers',
        'free_text_answer',
        'get_user_data'
    )
    list_filter = ('question', 'user_profile__gender')
    search_fields = (
        'question__text',
        'free_text_answer',
        'selected_answers__text'
    )
    readonly_fields = ('get_answers',)
    filter_horizontal = ('selected_answers',)
    list_per_page = 20
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('user_profile', 'question')
        }),
        ('Ответы', {
            'fields': ('selected_answers', 'free_text_answer'),
            'classes': ('collapse',),
        }),
    )

    def get_answers(self, obj):
        return ", ".join(a.text for a in obj.selected_answers.all())
    get_answers.short_description = 'Выбранные ответы'

    def get_user_data(self, obj):
        return (f"{obj.user_profile.gender or '-'}, "
                f"{obj.user_profile.age or '-'} лет, "
                f"{obj.user_profile.height or '-'} см, "
                f"{obj.user_profile.weight or '-'} кг")
    get_user_data.short_description = 'Анкетные данные'

    verbose_name = 'Ответ пользователя'
    verbose_name_plural = 'Ответы пользователей'
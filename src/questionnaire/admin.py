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

    user_profiles = AnonymousUserProfile.objects.prefetch_related(
        Prefetch('responses', queryset=UserResponse.objects.prefetch_related('selected_answers'))
    ).distinct()

    for profile in user_profiles:
        rating_data = calculate_user_rating(profile)

        # Основные данные
        row = [
            profile.responses.first().created_at.strftime('%Y-%m-%d %H:%M:%S') if profile.responses.exists() else '',
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
            answers = ", ".join(a.text for a in response_obj.selected_answers.all()) if response_obj else ""
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
            rating_data['total_score'],  # ИТОГО
            rating_data['rating']  # Оценка соответствия
        ]

        writer.writerow(row + special_columns)

    return response




# --- Блок для создания анкет (Questionnaire -> Question -> Answer) ---
class AnswerInline(nested_admin.NestedStackedInline):
    model = Answer
    extra = 0
    fields = ['text', 'value', 'is_optional', 'next_question']
    fk_name = 'question'
    classes = ['collapse']


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    list_display = ['text', 'order', 'is_required']
    inlines = [AnswerInline]
    ordering = ['order']
    actions = [export_responses_csv]
    save_on_top = True


@admin.register(AnonymousUserProfile)
class AnonymousUserProfileAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'gender', 'age', 'filled_survey']



# --- Блок для отображения ответов пользователей (UserResponse) ---
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

    def get_answers(self, obj):
        return ", ".join(a.text for a in obj.selected_answers.all())
    get_answers.short_description = 'Ответы'

    def get_user_data(self, obj):
        return (f"{obj.user_profile.gender or '-'}, "
                f"{obj.user_profile.age or '-'} лет, "
                f"{obj.user_profile.height or '-'} см, "
                f"{obj.user_profile.weight or '-'} кг")
    get_user_data.short_description = 'Данные пользователя'
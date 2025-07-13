import csv

from django.contrib import admin
import nested_admin
from django.db.models import Prefetch
from django.http import HttpResponse

from .models import Question, Answer, UserResponse, AnonymousUserProfile
from .utils import calculate_user_rating


@admin.action(description="Экспортировать ответы в CSV")
def export_responses_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="responses.csv"'

    writer = csv.writer(response, delimiter='\t')

    selected_question_ids = list(queryset.values_list('id', flat=True))
    questions = Question.objects.filter(id__in=selected_question_ids).order_by('order')
    all_questions = Question.objects.order_by('order')

    headers = [
        'Отметка времени', 'Пол', 'Возраст', 'Рост (см)', 'Вес (кг)', 'ИМТ',
        *all_questions.values_list('text', flat=True),
        'МБФ',
        'СТП',
        'Образ жизни и режим дня',
        'Питание',
        'Пищевое поведение',
        'Стресс',
        'ИТОГО',
        'Оценка соответствия'
    ]
    writer.writerow(headers)

    # Получаем только профили с ответами на выбранные вопросы
    user_profiles = AnonymousUserProfile.objects.filter(
        responses__question_id__in=selected_question_ids
    ).distinct().prefetch_related(
        Prefetch('responses',
                 queryset=UserResponse.objects.filter(
                     question_id__in=selected_question_ids
                 ).prefetch_related(
                     Prefetch('selected_answers', queryset=Answer.objects.only('text')),
                     'question'
                 )
        )
    )

    for profile in user_profiles:

        rating_data = calculate_user_rating(profile)
        first_response = profile.responses.earliest('created_at')

        # Расчет ИМТ
        bmi = ''
        if profile.height is not None and profile.weight is not None:
            try:
                if profile.height == 0:
                    raise ZeroDivisionError("Zero height")
                height_m = profile.height / 100
                bmi_value = profile.weight / (height_m ** 2)
                bmi = f"{bmi_value:.1f}"
            except ZeroDivisionError:
                bmi = 'Ошибка расчета'

        row = [
            first_response.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            profile.get_gender_display() if profile.gender else '',
            profile.age or '',
            profile.height or '',
            profile.weight or '',
            bmi,
        ]

        question_responses = {r.question_id: r for r in profile.responses.all()}
        answers_row = []
        for q in all_questions:
            response_obj = question_responses.get(q.id)
            if response_obj:
                if q.is_numeric_input:
                    answers = str(response_obj.numeric_answer or '')
                else:
                    selected = [a.text for a in response_obj.selected_answers.all()]
                    if response_obj.free_text_answer:
                        selected.append(response_obj.free_text_answer)
                    answers = ", ".join(selected) if selected else ""
            else:
                answers = "Нет ответа"
            answers_row.append(answers)

        row += answers_row

        special_columns = [
            rating_data.get('medico_biological_avg', 0),
            rating_data.get('work_assessment_avg', 0),
            rating_data.get('lifestyle_avg', 0),
            rating_data.get('nutrition_avg', 0),
            rating_data.get('eating_behavior_avg', 0),
            rating_data.get('stress_avg', 0),
            rating_data.get('total_score', 0),
            rating_data.get('rating', 'Нет оценки')
        ]

        writer.writerow(row + special_columns)

    return response


class AnswerInline(nested_admin.NestedStackedInline):
    model = Answer
    extra = 0
    fields = ['text', 'recommendation', 'value', 'next_question']
    fk_name = 'question'
    classes = ['collapse']
    verbose_name = 'Ответ'
    verbose_name_plural = 'Ответы'


@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    list_display = ['text', 'order', 'description', 'allow_free_text', 'is_multiple_choice', 'is_numeric_input']
    list_display_links = ['text']
    list_editable = ['order']  # Разрешаем редактирование порядка
    inlines = [AnswerInline]
    ordering = ['order']
    actions = [export_responses_csv]
    save_on_top = True
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('text', 'description', 'order')
        }),
        ('Тип вопроса', {
            'fields': ('is_required', 'is_numeric_input'),
            'classes': ('collapse',),
        }),
        ('Дополнительные настройки', {
            'fields': ('allow_free_text', 'is_multiple_choice'),
            'classes': ('collapse',),
            'description': 'Доступно только для не-числовых вопросов'
        }),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.is_numeric_input:
            # Скрываем дополнительные настройки для числовых вопросов
            return [fieldset for fieldset in fieldsets if fieldset[0] != 'Дополнительные настройки']
        return fieldsets

    def get_inlines(self, request, obj=None):
        if obj and obj.is_numeric_input:
            return []  # Скрываем варианты ответов для числовых вопросов
        return [AnswerInline]

    verbose_name = 'Вопрос'
    verbose_name_plural = 'Вопросы'

    class Media:
        js = (
            'admin/js/question_admin.js',
        )

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
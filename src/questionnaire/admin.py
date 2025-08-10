import csv

from django.contrib import admin
import nested_admin
from django.db.models import Prefetch
from django.http import HttpResponse

from .models import Question, Answer, UserResponse, AnonymousUserProfile
from .utils import calculate_user_rating


@admin.action(description="Экспортировать ответы в CSV")
def export_responses_csv(modeladmin, request, queryset):
    # Инициализация HTTP-ответа с CSV
    response = _create_csv_response()
    writer = csv.writer(response, delimiter='\t')

    # Получение данных вопросов
    selected_question_ids = list(queryset.values_list('id', flat=True))
    questions, all_questions = _get_questions_data(selected_question_ids)

    # Формирование заголовков CSV
    headers = _generate_csv_headers(all_questions)
    writer.writerow(headers)

    # Получение профилей пользователей с ответами
    user_profiles = _get_user_profiles_with_responses(selected_question_ids)

    # Запись данных по каждому профилю
    for profile in user_profiles:
        row = _build_profile_row(profile, all_questions)
        writer.writerow(row)

    return response


def _create_csv_response():
    """Создает HTTP-ответ с настройками для CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="responses.csv"'
    return response


def _get_questions_data(selected_ids):
    """Возвращает отобранные и все вопросы, упорядоченные по порядку"""
    questions = Question.objects.filter(id__in=selected_ids).order_by('order')
    all_questions = Question.objects.order_by('order')
    return questions, all_questions


def _generate_csv_headers(all_questions):
    """Генерирует заголовки для CSV файла"""
    base_headers = [
        'Отметка времени', 'Пол', 'Возраст', 'Рост (см)', 'Вес (кг)', 'ИМТ'
    ]
    question_headers = list(all_questions.values_list('text', flat=True))
    special_headers = [
        'МБФ', 'СТП', 'Образ жизни и режим дня', 'Питание',
        'Пищевое поведение', 'Стресс', 'ИТОГО', 'Оценка соответствия'
    ]
    return base_headers + question_headers + special_headers


def _get_user_profiles_with_responses(question_ids):
    """Получает профили пользователей с предзагруженными ответами на вопросы"""
    return AnonymousUserProfile.objects.filter(
        responses__question_id__in=question_ids
    ).distinct().prefetch_related(
        Prefetch('responses',
                 queryset=UserResponse.objects.filter(
                     question_id__in=question_ids
                     ).prefetch_related(
                         Prefetch('selected_answers', queryset=Answer.objects.only('text')),
                         'question'
                     )
                 )
    )


def _calculate_bmi(profile):
    """Рассчитывает ИМТ на основе данных профиля"""
    # TODO: Вынести расчет ИМТ в метод модели или утилитарную функцию
    if profile.height is None or profile.weight is None:
        return ''

    try:
        if profile.height == 0:
            raise ZeroDivisionError("Рост не может быть 0")
        height_m = profile.height / 100
        bmi_value = profile.weight / (height_m ** 2)
        return f"{bmi_value:.1f}"
    except ZeroDivisionError:
        return 'Ошибка расчета'


def _build_profile_row(profile, all_questions):
    """Формирует строку данных для профиля пользователя"""
    # Базовые данные профиля
    first_response = profile.responses.earliest('created_at')
    base_data = [
        first_response.created_at.strftime('%Y-%m-%d'),
        profile.get_gender_display() if profile.gender else '',
        profile.age or '',
        profile.height or '',
        profile.weight or '',
        _calculate_bmi(profile),
    ]

    # Данные ответов на вопросы
    responses_data = _get_responses_data(profile, all_questions)

    # Специальные рейтинговые данные
    rating_data = calculate_user_rating(profile)
    rating_columns = [
        rating_data.get('medico_biological_avg', 0),
        rating_data.get('work_assessment_avg', 0),
        rating_data.get('lifestyle_avg', 0),
        rating_data.get('nutrition_avg', 0),
        rating_data.get('eating_behavior_avg', 0),
        rating_data.get('stress_avg', 0),
        rating_data.get('total_score', 0),
        rating_data.get('rating', 'Нет оценки')
    ]

    return base_data + responses_data + rating_columns


def _get_responses_data(profile, all_questions):
    """Извлекает данные ответов для всех вопросов"""
    # TODO: Рассмотреть оптимизацию через кеширование question_responses
    question_responses = {r.question_id: r for r in profile.responses.all()}
    responses_data = []

    for question in all_questions:
        response_obj = question_responses.get(question.id)
        responses_data.append(_format_response_value(response_obj, question))

    return responses_data


def _format_response_value(response_obj, question):
    """Форматирует значение ответа в читаемую строку"""
    if not response_obj:
        return "Нет ответа"

    if question.is_numeric_input:
        return str(response_obj.numeric_answer or '')

    # Текстовые/выборные ответы
    selected = [a.text for a in response_obj.selected_answers.all()]
    if response_obj.free_text_answer:
        selected.append(response_obj.free_text_answer)

    return ", ".join(selected) if selected else ""


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
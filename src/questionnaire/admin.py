import csv
from collections import defaultdict

from django.contrib import admin
import nested_admin
from django.http import HttpResponse

from .models import Questionnaire, Question, Answer, UserResponse, AnonymousUserProfile


@admin.action(description="Экспортировать ответы в CSV")
def export_responses_csv(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(request, "Выберите один опросник для экспорта", level="error")
        return

    questionnaire = queryset.first()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="responses_{questionnaire.title}.csv"'

    writer = csv.writer(response, delimiter='\t')

    questions = questionnaire.questions.all()
    question_texts = [q.text for q in questions]

    # Дополнительные столбцы
    extra_columns = ['МБФ', 'ФАиРД', 'СТП', 'Образ жизни', 'Питание', 'Пищевое поведение', 'Продукты питания', 'Стресс']
    headers = (
        ['Отметка времени', 'Пол', 'Сколько Вам лет?', 'Рост (в см)', 'Вес (в кг)'] +
        question_texts +
        extra_columns +
        ['ИТОГО', 'Оценка уровня соответствия гигиеническим требованиям']
    )
    writer.writerow(headers)

    # Определяем вопросы по категориям
    stress_questions = {q.id for q in questions.filter(description="СТРЕСС")}
    nutrition_questions = {q.id for q in questions.filter(description="ПИТАНИЕ")}
    eating_behavior_questions = {q.id for q in questions.filter(description="Как часто Вы употребляете следующие продукты и напитки")}
    work_assessment_questions = {q.id for q in questions.filter(description="САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА")}

    responses_by_user = defaultdict(
        lambda: {
            'created_at': None, 'gender': '', 'age': '', 'height': '', 'weight': '',
            'answers': {}, 'stress_values': [], 'nutrition_values': [],
            'eating_behavior_values': [], 'work_assessment_values': []
        }
    )

    responses = UserResponse.objects.filter(questionnaire=questionnaire).select_related('question', 'selected_answer')

    for response_obj in responses:
        session_key = response_obj.session_key
        user_profile = AnonymousUserProfile.objects.filter(session_key=session_key).first()

        if user_profile:
            responses_by_user[session_key]['gender'] = user_profile.gender or ''
            responses_by_user[session_key]['age'] = user_profile.age or ''
            responses_by_user[session_key]['height'] = user_profile.height or ''
            responses_by_user[session_key]['weight'] = user_profile.weight or ''

        responses_by_user[session_key]['created_at'] = response_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

        answer_text = response_obj.selected_answer.text if response_obj.selected_answer else response_obj.free_text_answer
        responses_by_user[session_key]['answers'][response_obj.question.text] = answer_text

        # Если есть числовое значение ответа, добавляем его в соответствующую категорию
        if response_obj.selected_answer and response_obj.selected_answer.value is not None:
            if response_obj.question.id in stress_questions:
                responses_by_user[session_key]['stress_values'].append(response_obj.selected_answer.value)
            elif response_obj.question.id in nutrition_questions:
                responses_by_user[session_key]['nutrition_values'].append(response_obj.selected_answer.value)
            elif response_obj.question.id in eating_behavior_questions:
                responses_by_user[session_key]['eating_behavior_values'].append(response_obj.selected_answer.value)
            elif response_obj.question.id in work_assessment_questions:
                responses_by_user[session_key]['work_assessment_values'].append(response_obj.selected_answer.value)

    # Записываем строки с ответами
    for session_key, data in responses_by_user.items():
        stress_avg = sum(data['stress_values']) / len(data['stress_values']) if data['stress_values'] else ''
        nutrition_avg = sum(data['nutrition_values']) / len(data['nutrition_values']) if data['nutrition_values'] else ''
        eating_behavior_avg = sum(data['eating_behavior_values']) / len(data['eating_behavior_values']) if data['eating_behavior_values'] else ''
        work_assessment_avg = sum(data['work_assessment_values']) / len(data['work_assessment_values']) if data['work_assessment_values'] else ''

        # Собираем значения для столбца ИТОГО (только числа)
        extra_values = [stress_avg, nutrition_avg, eating_behavior_avg, work_assessment_avg]
        extra_values = [v for v in extra_values if isinstance(v, (int, float))]  # Убираем пустые значения
        total_score = sum(extra_values) / len(extra_values) if extra_values else ''

        # Оценка уровня соответствия гигиеническим требованиям
        if isinstance(total_score, (int, float)):
            if total_score <= 0.47:
                hygiene_rating = "Неудовлетворительная"
            elif 0.47 < total_score <= 0.67:
                hygiene_rating = "Удовлетворительная"
            elif 0.67 < total_score <= 0.89:
                hygiene_rating = "Хорошая"
            elif 0.9 <= total_score <= 1:
                hygiene_rating = "Оптимальная"
            else:
                hygiene_rating = ""
        else:
            hygiene_rating = ""

        row = [
            data['created_at'],
            data['gender'],
            data['age'],
            data['height'],
            data['weight'],
        ] + [data['answers'].get(q, '') for q in question_texts] + [
            '', '', work_assessment_avg, '', nutrition_avg, eating_behavior_avg, '', stress_avg, total_score, hygiene_rating
        ]  # Остальные столбцы пока пустые

        writer.writerow(row)

    return response




# --- Блок для создания анкет (Questionnaire -> Question -> Answer) ---
class AnswerInline(nested_admin.NestedStackedInline):
    model = Answer
    extra = 0
    fields = ['text', 'value', 'is_optional', 'next_question']
    fk_name = 'question'
    classes = ['collapse']

class QuestionInline(nested_admin.NestedStackedInline):
    model = Question
    extra = 0
    fields = ['text', 'description', 'allow_free_text']  # Добавляем поле description
    inlines = [AnswerInline]

@admin.register(Questionnaire)
class QuestionnaireAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'description')  # Показываем описание анкеты
    inlines = [QuestionInline]
    actions = [export_responses_csv]
    save_on_top = True

# --- Блок для отображения ответов пользователей (UserResponse) ---
@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = (
        'questionnaire',
        'created_at',
        'question',
        'selected_answer',
        'free_text_answer',
        'get_user_profile_gender',  # Кастомный метод
        'get_user_profile_age',     # Кастомный метод
        'get_user_profile_height',  # Кастомный метод
        'get_user_profile_weight',  # Кастомный метод
    )
    list_filter = ('questionnaire', 'question')
    search_fields = ('question__text', 'selected_answer__text', 'free_text_answer')
    list_select_related = ('question', 'selected_answer', 'questionnaire')

    # Методы для получения данных из AnonymousUserProfile
    def get_user_profile_gender(self, obj):
        profile = AnonymousUserProfile.objects.filter(session_key=obj.session_key).first()
        return profile.gender if profile else '—'
    get_user_profile_gender.short_description = 'Пол'

    def get_user_profile_age(self, obj):
        profile = AnonymousUserProfile.objects.filter(session_key=obj.session_key).first()
        return profile.age if profile else '—'
    get_user_profile_age.short_description = 'Возраст'

    def get_user_profile_height(self, obj):
        profile = AnonymousUserProfile.objects.filter(session_key=obj.session_key).first()
        return profile.height if profile else '—'
    get_user_profile_height.short_description = 'Рост'

    def get_user_profile_weight(self, obj):
        profile = AnonymousUserProfile.objects.filter(session_key=obj.session_key).first()
        return profile.weight if profile else '—'
    get_user_profile_weight.short_description = 'Вес'

    # Оптимизация запросов к БД
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('questionnaire', 'question')


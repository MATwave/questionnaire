import csv
from collections import defaultdict

from django.contrib import admin
import nested_admin
from django.http import HttpResponse

from .models import Question, Answer, UserResponse, AnonymousUserProfile


@admin.action(description="Экспортировать ответы в CSV")
def export_responses_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="responses.csv"'

    writer = csv.writer(response, delimiter='\t')

    questions = Question.objects.all().order_by('order')
    question_texts = [q.text for q in questions]

    headers = (
            ['Отметка времени', 'Пол', 'Возраст', 'Рост (см)', 'Вес (кг)'] +
            question_texts +
            ['МБФ', 'ФАиРД', 'СТП', 'Образ жизни', 'Питание',
             'Пищевое поведение', 'Продукты питания', 'Стресс',
             'ИТОГО', 'Оценка соответствия']
    )
    writer.writerow(headers)

    # Определение категорий вопросов
    stress_questions = {q.id for q in questions.filter(description="СТРЕСС")}
    nutrition_questions = {q.id for q in questions.filter(description="ПИТАНИЕ")}
    eating_behavior_questions = {q.id for q in questions.filter(
        description="Как часто Вы употребляете следующие продукты и напитки")}
    work_assessment_questions = {q.id for q in questions.filter(
        description="САМООЦЕНКА ТРУДОВОГО ПРОЦЕССА")}

    responses_by_user = defaultdict(
        lambda: {
            'created_at': None, 'gender': '', 'age': '',
            'height': '', 'weight': '', 'answers': {},
            'stress_values': [], 'nutrition_values': [],
            'eating_behavior_values': [], 'work_assessment_values': []
        }
    )

    responses = UserResponse.objects.prefetch_related('selected_answers').select_related('user_profile', 'question')

    for response_obj in responses:
        user_profile = response_obj.user_profile
        user_data = responses_by_user[user_profile.id]

        # Основные данные профиля
        user_data.update({
            'gender': user_profile.gender or '',
            'age': user_profile.age or '',
            'height': user_profile.height or '',
            'weight': user_profile.weight or '',
            'created_at': response_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

        # Обработка ответов
        answers_text = []
        values = []

        for answer in response_obj.selected_answers.all():
            answers_text.append(answer.text)
            if answer.value is not None:
                values.append(answer.value)

        # Сохраняем текст ответов
        user_data['answers'][response_obj.question.text] = ", ".join(answers_text)

        # Распределение значений по категориям
        q_id = response_obj.question.id
        for val in values:
            if q_id in stress_questions:
                user_data['stress_values'].append(val)
            elif q_id in nutrition_questions:
                user_data['nutrition_values'].append(val)
            elif q_id in eating_behavior_questions:
                user_data['eating_behavior_values'].append(val)
            elif q_id in work_assessment_questions:
                user_data['work_assessment_values'].append(val)

    # Формирование строк отчета
    for user_id, data in responses_by_user.items():
        # Расчет средних значений
        def avg(values):
            return sum(values) / len(values) if values else ''

        stress_avg = avg(data['stress_values'])
        nutrition_avg = avg(data['nutrition_values'])
        eating_avg = avg(data['eating_behavior_values'])
        work_avg = avg(data['work_assessment_values'])

        # Общий балл
        total_values = [v for v in [stress_avg, nutrition_avg, eating_avg, work_avg]
                        if isinstance(v, (int, float))]
        total_score = avg(total_values) if total_values else ''

        # Оценка соответствия
        if isinstance(total_score, float):
            if total_score <= 0.47:
                rating = "Неудовлетворительная"
            elif 0.47 < total_score <= 0.67:
                rating = "Удовлетворительная"
            elif 0.67 < total_score <= 0.89:
                rating = "Хорошая"
            else:
                rating = "Оптимальная"
        else:
            rating = ""

        row = [
            data['created_at'],
            data['gender'],
            data['age'],
            data['height'],
            data['weight'],
            *[data['answers'].get(q.text, '') for q in questions],
            '', '', work_avg, '', nutrition_avg, eating_avg, '', stress_avg,
            total_score,
            rating
        ]

        writer.writerow(row)

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
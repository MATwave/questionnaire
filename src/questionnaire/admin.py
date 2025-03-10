from django.contrib import admin
from .models import Questionnaire, Question, Answer

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    fk_name = 'question'  # указываем, что для инлайнов это основной внешний ключ (ссылается на 'question')

class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]

admin.site.register(Questionnaire)
admin.site.register(Question, QuestionAdmin)

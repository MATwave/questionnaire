from django.contrib import admin
from .models import Questionnaire, Question, Answer, UserResponse

class UserResponseAdmin(admin.ModelAdmin):
    list_display = ('questionnaire', 'question', 'selected_answer', 'free_text_answer')
    list_filter = ('questionnaire',)
    search_fields = ('question__text', 'selected_answer__text', 'free_text_answer')

admin.site.register(Questionnaire)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(UserResponse, UserResponseAdmin)

from django.contrib import admin
from .models import PYQuestion


@admin.register(PYQuestion)
class PYQuestionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'topic', 'year', 'exam_name', 'marks', 'is_important')
    list_filter = ('subject', 'year', 'is_important')
    search_fields = ('question', 'subject', 'topic')
    list_editable = ('is_important',)

from django.contrib import admin
from .models import Essay

@admin.register(Essay)
class EssayAdmin(admin.ModelAdmin):
    list_display = ('title', 'student_name', 'score_overall', 'created_at')
    search_fields = ('title', 'student_name', 'content')
    readonly_fields = ('score_overall','score_length','score_clarity','score_vocabulary','score_readability','feedback','created_at')

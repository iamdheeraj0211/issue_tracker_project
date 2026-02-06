from django.contrib import admin
from .models import Issue, Comment, Label
# Register your models here.

def get_all_fields(model):
    return [field.name for field in model._meta.fields]
@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Label)

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Issue)
    list_filter = ('status', 'assignee', 'labels')
    search_fields = ('title', 'description')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Comment)
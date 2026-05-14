from django.contrib import admin
from .models import ABTestAssignment, ABTestEvent


@admin.register(ABTestAssignment)
class ABTestAssignmentAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'test_name', 'variant_id', 'assigned_at']
    list_filter = ['test_name', 'variant_id', 'assigned_at']
    search_fields = ['test_name']
    readonly_fields = ['assigned_at']


@admin.register(ABTestEvent)
class ABTestEventAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'test_name', 'variant_id', 'event_type', 'path', 'created_at']
    list_filter = ['test_name', 'variant_id', 'event_type', 'created_at']
    search_fields = ['test_name', 'event_type']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

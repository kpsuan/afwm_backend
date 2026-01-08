from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'read_at', 'created_at')
    search_fields = ('title', 'body', 'user__email', 'user__display_name')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)

    def is_read(self, obj):
        return obj.read_at is not None
    is_read.boolean = True
    is_read.short_description = 'Read'

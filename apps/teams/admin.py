from django.contrib import admin
from .models import Team, TeamMembership, PendingInvitation


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    readonly_fields = ('id', 'created_at', 'updated_at')
    fields = ('user', 'role', 'status', 'invited_by', 'joined_at')


class PendingInvitationInline(admin.TabularInline):
    model = PendingInvitation
    extra = 0
    readonly_fields = ('id', 'created_at', 'invitation_token')
    fields = ('email', 'role', 'invited_by', 'expires_at')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'team_level', 'created_at', 'is_deleted')
    list_filter = ('team_level', 'deleted_at')
    search_fields = ('name', 'description', 'created_by__email', 'created_by__display_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [TeamMembershipInline, PendingInvitationInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'avatar_url')
        }),
        ('Team Info', {
            'fields': ('created_by', 'team_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'status', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('user__email', 'user__display_name', 'team__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    raw_id_fields = ('user', 'team', 'invited_by', 'guardian_override', 'emergency_contact_override')


@admin.register(PendingInvitation)
class PendingInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'team', 'role', 'invited_by', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('role',)
    search_fields = ('email', 'team__name', 'invited_by__email')
    readonly_fields = ('id', 'created_at', 'invitation_token')
    ordering = ('-created_at',)
    raw_id_fields = ('team', 'invited_by')

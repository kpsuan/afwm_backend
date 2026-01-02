import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User

# Set up logging for sensitive data access
logger = logging.getLogger('accounts.admin')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model with RBAC and data masking."""

    list_display = ('email', 'display_name', 'masked_phone_display', 'is_hcw', 'email_verified', 'is_staff', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_hcw', 'email_verified')
    search_fields = ('email', 'display_name', 'first_name', 'last_name')
    ordering = ('-created_at',)

    def masked_phone_display(self, obj):
        """Display masked phone number in list view. Superusers see full number."""
        if not obj.phone_number:
            return '-'
        # Superusers see everything
        if self.has_view_permission(self.request) and self.request.user.is_superuser:
            return obj.phone_number
        # Staff users see masked
        return self._mask_phone(obj.phone_number)
    masked_phone_display.short_description = 'Phone'

    def _mask_phone(self, phone):
        """Mask phone number: (555) ***-4567"""
        if not phone or len(phone) < 4:
            return '***-****'
        # Show last 4 digits
        return f"***-{phone[-4:]}"

    def _mask_birth_date(self, birth_date):
        """Mask birth date: show only year"""
        if not birth_date:
            return None
        return f"{birth_date.year}-**-**"

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on user permissions."""
        self.request = request  # Store request for use in other methods

        if request.user.is_superuser:
            # Superusers see everything unmasked
            return (
                (None, {'fields': ('email', 'password')}),
                ('Personal Info', {
                    'fields': ('display_name', 'first_name', 'last_name', 'profile_photo_url',
                              'bio', 'pronouns', 'phone_number', 'birth_date', 'location')
                }),
                ('HCW Status', {'fields': ('is_hcw', 'hcw_attested_at')}),
                ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                ('Email Verification', {'fields': ('email_verified', 'email_verification_token', 'email_verification_sent_at')}),
                ('OAuth', {'fields': ('google_id',)}),
                ('Important dates', {'fields': ('last_login_at', 'created_at', 'updated_at', 'deleted_at')}),
            )
        else:
            # Regular staff see masked sensitive data
            return (
                (None, {'fields': ('email',)}),
                ('Personal Info', {
                    'fields': ('display_name', 'first_name', 'last_name', 'profile_photo_url', 'bio', 'pronouns'),
                    'description': 'Sensitive fields (phone, birth date, location) are hidden for privacy.'
                }),
                ('HCW Status', {'fields': ('is_hcw',)}),
                ('Permissions', {'fields': ('is_active',)}),
                ('Important dates', {'fields': ('last_login_at', 'created_at')}),
            )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'password1', 'password2', 'is_hcw'),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login_at', 'hcw_attested_at')

    # Use email as the username field
    USERNAME_FIELD = 'email'

    def has_change_permission(self, request, obj=None):
        """
        Regular staff can view users but cannot edit sensitive fields.
        Superusers can do everything.
        """
        return super().has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Make sensitive fields readonly for non-superusers."""
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser and obj:
            # Non-superusers cannot edit these sensitive fields
            readonly.extend(['phone_number', 'birth_date', 'location', 'email'])
        return readonly

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Log access to user details for audit trail."""
        try:
            obj = self.get_object(request, object_id)
            if obj:
                logger.info(
                    f"User detail accessed: {request.user.email} viewed user {obj.email} "
                    f"(ID: {object_id}) | IP: {self._get_client_ip(request)}"
                )
        except Exception as e:
            logger.error(f"Error logging user access: {e}")

        return super().change_view(request, object_id, form_url, extra_context)

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

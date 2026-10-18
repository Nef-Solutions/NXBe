from django.contrib import admin
from .models import User, ProfessionalProfile, VerificationCaseMessage

class ProfessionalProfileInline(admin.StackedInline):
    model = ProfessionalProfile
    can_delete = False
    verbose_name_plural = 'Perfil Profesional Asociado'
    fk_name = 'user'

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'account_status', 'is_staff', 'is_active')
    list_filter = ('role', 'account_status', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    inlines = (ProfessionalProfileInline,)
    
    fieldsets = (
        ('Credenciales e Identidad', {'fields': ('email', 'username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'rut', 'phone', 'address', 'commune', 'profile_photo')}),
        ('Privacidad y Seguridad', {'fields': ('privacy_policy_accepted_at', 'privacy_policy_version', 'account_status', 'failed_login_attempts', 'locked_until')}),
        ('Permisos y Rol', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'verification_status', 'visit_fee', 'rating_avg')
    list_filter = ('verification_status',)
    search_fields = ('rut', 'user__first_name', 'user__last_name', 'user__email')
    list_editable = ('verification_status',)


@admin.register(VerificationCaseMessage)
class VerificationCaseMessageAdmin(admin.ModelAdmin):
    list_display = ('professional', 'created_at', 'resolved_at')
    list_filter = ('resolved_at',)
    search_fields = ('professional__user__email', 'message', 'admin_response')


from apps.visits.models import AdminAuditLog, AfterSalesClaim, ContentProgress, Notification, ProfessionalContent, Rating, SupportTicket, VisitRequest


@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'professional', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('client__email', 'professional__user__email')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('visit', 'author', 'target', 'quality', 'punctuality', 'treatment', 'created_at')
    list_filter = ('quality', 'punctuality', 'treatment')


@admin.register(AfterSalesClaim)
class AfterSalesClaimAdmin(admin.ModelAdmin):
    list_display = ('visit', 'client', 'status', 'created_at', 'resolved_at')
    list_filter = ('status',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'subject')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)


@admin.register(ProfessionalContent)
class ProfessionalContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'is_visible', 'order')
    list_filter = ('module', 'is_visible')
    list_editable = ('is_visible', 'order')


@admin.register(ContentProgress)
class ContentProgressAdmin(admin.ModelAdmin):
    list_display = ('professional', 'content', 'completed_at')


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('administrator', 'action', 'target_type', 'target_id', 'created_at')
    list_filter = ('action', 'target_type')
    readonly_fields = ('administrator', 'action', 'reason', 'target_type', 'target_id', 'created_at')
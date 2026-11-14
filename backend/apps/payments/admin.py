from django.contrib import admin

from .models import PaymentTransaction, ProfessionalSubscriptionPlan


@admin.register(ProfessionalSubscriptionPlan)
class ProfessionalSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'amount', 'duration_months', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'buy_order', 'payer', 'amount', 'status', 'visit',
        'professional', 'subscription_plan', 'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('buy_order', 'payer__email')
    readonly_fields = (
        'visit', 'professional', 'subscription_plan', 'subscription_duration_months',
        'payer', 'amount', 'buy_order', 'session_id', 'token_hash',
        'response_code', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

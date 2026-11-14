from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.authentication.models import ProfessionalProfile
from apps.visits.models import VisitRequest


class ProfessionalSubscriptionPlan(models.Model):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    duration_months = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='subscription_plan_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(duration_months__gt=0),
                name='subscription_plan_duration_positive',
            ),
            models.UniqueConstraint(
                fields=('is_active',),
                condition=models.Q(is_active=True),
                name='only_one_active_subscription_plan',
            ),
        ]

    def __str__(self):
        return self.name


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        AUTHORIZED = 'AUTHORIZED', 'Autorizado'
        REJECTED = 'REJECTED', 'Rechazado'
        FAILED = 'FAILED', 'Fallido'

    visit = models.ForeignKey(
        VisitRequest,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
    )
    professional = models.ForeignKey(
        ProfessionalProfile,
        on_delete=models.PROTECT,
        related_name='subscription_payments',
        null=True,
        blank=True,
    )
    subscription_plan = models.ForeignKey(
        ProfessionalSubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
    )
    subscription_duration_months = models.PositiveSmallIntegerField(default=1)
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    buy_order = models.CharField(max_length=26, unique=True)
    session_id = models.CharField(max_length=61)
    token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    response_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(visit__isnull=False, professional__isnull=True)
                    | Q(visit__isnull=True, professional__isnull=False)
                ),
                name='payment_has_exactly_one_target',
            ),
            models.CheckConstraint(
                condition=(
                    Q(subscription_plan__isnull=True)
                    | Q(visit__isnull=True, professional__isnull=False)
                ),
                name='subscription_plan_only_for_professional_payment',
            ),
        ]

    def __str__(self):
        return f'Pago {self.buy_order} [{self.status}]'

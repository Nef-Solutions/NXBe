from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AssistantDailyUsage


class AssistantQuotaExceeded(Exception):
    pass


def reserve_daily_request(user):
    today = timezone.localdate()
    with transaction.atomic():
        global_usage, _ = AssistantDailyUsage.objects.get_or_create(
            user=None,
            date=today,
        )
        global_usage = AssistantDailyUsage.objects.select_for_update().get(
            pk=global_usage.pk,
        )
        user_usage, _ = AssistantDailyUsage.objects.get_or_create(
            user=user,
            date=today,
        )
        user_usage = AssistantDailyUsage.objects.select_for_update().get(
            pk=user_usage.pk,
        )

        if user_usage.request_count >= settings.ASSISTANT_DAILY_USER_LIMIT:
            raise AssistantQuotaExceeded('Alcanzaste el límite diario del asistente.')
        if global_usage.request_count >= settings.ASSISTANT_DAILY_GLOBAL_LIMIT:
            raise AssistantQuotaExceeded('El asistente alcanzó el límite diario de pruebas.')

        user_usage.request_count += 1
        global_usage.request_count += 1
        user_usage.save(update_fields=('request_count',))
        global_usage.save(update_fields=('request_count',))

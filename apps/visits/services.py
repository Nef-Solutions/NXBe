from datetime import timedelta

from django.utils import timezone

from .models import Notification, VisitRequest


def expire_pending_requests(now=None):
    now = now or timezone.now()
    threshold = now - timedelta(days=30)
    pending = VisitRequest.objects.filter(status=VisitRequest.Status.PENDING, created_at__lte=threshold).select_related('client', 'professional__user')
    expired_count = 0
    for visit in pending:
        visit.status = VisitRequest.Status.EXPIRED
        visit.save(update_fields=['status', 'updated_at'])
        Notification.objects.create(
            recipient=visit.client,
            title='Solicitud vencida',
            message='La solicitud superó el plazo de respuesta. Puedes solicitar otra visita.',
            related_visit=visit,
        )
        expired_count += 1
    return expired_count
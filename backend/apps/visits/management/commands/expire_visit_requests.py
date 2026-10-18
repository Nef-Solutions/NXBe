from django.core.management.base import BaseCommand

from apps.visits.services import expire_pending_requests


class Command(BaseCommand):
    help = 'Vence solicitudes pendientes con más de 30 días y notifica al cliente.'

    def handle(self, *args, **options):
        count = expire_pending_requests()
        self.stdout.write(self.style.SUCCESS(f'{count} solicitud(es) vencida(s).'))
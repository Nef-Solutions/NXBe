from django.db import models
from django.db.models import Q

from django.conf import settings


class AssistantDailyUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='assistant_daily_usage',
    )
    date = models.DateField()
    request_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'date'),
                condition=Q(user__isnull=False),
                name='assistant_user_daily_unique',
            ),
            models.UniqueConstraint(
                fields=('date',),
                condition=Q(user__isnull=True),
                name='assistant_global_daily_unique',
            ),
        ]
        indexes = [models.Index(fields=('date', 'user'))]

    def __str__(self):
        scope = f'user {self.user_id}' if self.user_id else 'global'
        return f'Assistant usage {scope} ({self.date}): {self.request_count}'

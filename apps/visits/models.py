from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.authentication.models import ProfessionalProfile
from apps.catalog.models import Specialty


class VisitRequest(models.Model):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pendiente'
		ACCEPTED = 'ACCEPTED', 'Aceptada'
		REJECTED = 'REJECTED', 'Rechazada'
		CANCELLED = 'CANCELLED', 'Cancelada'
		EXPIRED = 'EXPIRED', 'Vencida'
		PROFESSIONAL_FINISHED = 'PROFESSIONAL_FINISHED', 'Finalizada por profesional'
		COMPLETED = 'COMPLETED', 'Completada'
		FORCED_CLOSED = 'FORCED_CLOSED', 'Cerrada por administración'

	client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='visit_requests')
	professional = models.ForeignKey(ProfessionalProfile, on_delete=models.PROTECT, related_name='visit_requests')
	specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name='visit_requests')
	problem_description = models.TextField()
	tentative_schedule = models.CharField(max_length=255, blank=True)
	visit_address = models.CharField(max_length=255)
	status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
	rejection_reason = models.TextField(blank=True)
	professional_confirmed_at = models.DateTimeField(null=True, blank=True)
	client_confirmed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-created_at',)

	def accept(self):
		if self.status != self.Status.PENDING:
			raise ValueError('Solo se pueden aceptar solicitudes pendientes.')
		if self.professional.verification_status != ProfessionalProfile.VerificationStatus.APPROVED:
			raise ValueError('El profesional no está verificado.')
		self.status = self.Status.ACCEPTED
		self.save(update_fields=['status', 'updated_at'])

	def reject(self, reason):
		if self.status != self.Status.PENDING:
			raise ValueError('Solo se pueden rechazar solicitudes pendientes.')
		if not reason:
			raise ValueError('El rechazo requiere un motivo.')
		self.status = self.Status.REJECTED
		self.rejection_reason = reason
		self.save(update_fields=['status', 'rejection_reason', 'updated_at'])

	def cancel(self):
		if self.status != self.Status.PENDING:
			raise ValueError('Solo se pueden cancelar solicitudes pendientes.')
		self.status = self.Status.CANCELLED
		self.save(update_fields=['status', 'updated_at'])

	def finish_by_professional(self):
		if self.status != self.Status.ACCEPTED:
			raise ValueError('Solo se pueden finalizar servicios aceptados.')
		self.status = self.Status.PROFESSIONAL_FINISHED
		self.professional_confirmed_at = timezone.now()
		self.save(update_fields=['status', 'professional_confirmed_at', 'updated_at'])

	def confirm_by_client(self):
		if self.status not in (self.Status.ACCEPTED, self.Status.PROFESSIONAL_FINISHED):
			raise ValueError('El cliente solo puede confirmar un servicio activo.')
		self.client_confirmed_at = timezone.now()
		if self.professional_confirmed_at:
			self.status = self.Status.COMPLETED
		self.save(update_fields=['status', 'client_confirmed_at', 'updated_at'])


class Rating(models.Model):
	visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE, related_name='ratings')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ratings_given')
	target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ratings_received')
	quality = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	punctuality = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	treatment = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	comment = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('visit', 'author'), name='unique_rating_per_author_visit')]


class AfterSalesClaim(models.Model):
	class Status(models.TextChoices):
		OPEN = 'OPEN', 'Abierto'
		PROFESSIONAL_RESPONDED = 'PROFESSIONAL_RESPONDED', 'Respondido por profesional'
		ESCALATED = 'ESCALATED', 'Escalado'
		RESOLVED = 'RESOLVED', 'Resuelto'

	visit = models.OneToOneField(VisitRequest, on_delete=models.CASCADE, related_name='after_sales_claim')
	client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='claims_opened')
	description = models.TextField()
	professional_response = models.TextField(blank=True)
	admin_resolution = models.TextField(blank=True)
	status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
	created_at = models.DateTimeField(auto_now_add=True)
	resolved_at = models.DateTimeField(null=True, blank=True)


class SupportTicket(models.Model):
	class Status(models.TextChoices):
		OPEN = 'OPEN', 'Abierto'
		IN_REVIEW = 'IN_REVIEW', 'En revisión'
		RESOLVED = 'RESOLVED', 'Resuelto'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='support_tickets')
	visit = models.ForeignKey(VisitRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
	subject = models.CharField(max_length=160)
	description = models.TextField()
	response = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
	recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
	title = models.CharField(max_length=160)
	message = models.TextField()
	related_visit = models.ForeignKey(VisitRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-created_at',)


class ProfessionalContent(models.Model):
	class Module(models.TextChoices):
		TAX = 'TAX', 'Tributario'
		SAFETY = 'SAFETY', 'Seguridad'
		MANAGEMENT = 'MANAGEMENT', 'Gestión'

	title = models.CharField(max_length=160)
	description = models.TextField(blank=True)
	module = models.CharField(max_length=20, choices=Module.choices)
	url = models.URLField()
	is_external = models.BooleanField(default=False)
	is_visible = models.BooleanField(default=True)
	order = models.PositiveIntegerField(default=0)


class ContentProgress(models.Model):
	professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name='content_progress')
	content = models.ForeignKey(ProfessionalContent, on_delete=models.CASCADE, related_name='progress')
	completed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('professional', 'content'), name='unique_content_progress')]


class AdminAuditLog(models.Model):
	administrator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='admin_actions')
	action = models.CharField(max_length=120)
	reason = models.TextField()
	target_type = models.CharField(max_length=120)
	target_id = models.PositiveBigIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-created_at',)

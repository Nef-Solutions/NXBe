from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .validators import sanitize_person_name, validate_rut_chileno

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', 'Cliente'
        PROFESSIONAL = 'PROFESSIONAL', 'Profesional'
        ADMIN = 'ADMIN', 'Administrador'

    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Activa'
        SUSPENDED = 'SUSPENDED', 'Suspendida'
        BLOCKED = 'BLOCKED', 'Bloqueada'
        DEACTIVATED = 'DEACTIVATED', 'Dada de baja'

    email = models.EmailField('Correo electrónico', unique=True)
    role = models.CharField('Rol', max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField('Teléfono', max_length=20, blank=True)
    rut = models.CharField('RUT', max_length=12, unique=True, null=True, blank=True)
    address = models.CharField('Dirección', max_length=255, blank=True)
    commune = models.CharField('Comuna', max_length=120, blank=True)
    privacy_policy_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_policy_version = models.CharField(max_length=30, blank=True)
    account_status = models.CharField(max_length=20, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def clean(self):
        super().clean()
        if self.first_name:
            self.first_name = sanitize_person_name(self.first_name)
        if self.last_name:
            self.last_name = sanitize_person_name(self.last_name)
        if self.rut:
            self.rut = validate_rut_chileno(self.rut)

    def accept_privacy_policy(self, version):
        self.privacy_policy_accepted_at = timezone.now()
        self.privacy_policy_version = version

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.email}) [{self.role}]"


class ProfessionalProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        APPROVED = 'APPROVED', 'Aprobado'
        REJECTED = 'REJECTED', 'Rechazado'

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='professional_profile'
    )
    rut = models.CharField('RUT', max_length=12, unique=True)
    id_card_front = models.ImageField(
        'Foto frontal cédula', 
        upload_to='verifications/id_front/', 
        blank=True
    )
    id_card_back = models.ImageField(
        'Foto trasera cédula', 
        upload_to='verifications/id_back/', 
        blank=True
    )
    verification_status = models.CharField(
        'Estado de verificación',
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    visit_fee = models.DecimalField('Tarifa de visita ($CLP)', max_digits=10, decimal_places=0, default=0)
    rating_avg = models.DecimalField('Calificación promedio', max_digits=3, decimal_places=2, default=0.0)

    class Meta:
        verbose_name = 'Perfil Profesional'
        verbose_name_plural = 'Perfiles Profesionales'

    def clean(self):
        super().clean()
        if self.rut:
            self.rut = validate_rut_chileno(self.rut)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profesional: {self.user.get_full_name()} - RUT: {self.rut} [{self.verification_status}]"


class VerificationCaseMessage(models.Model):
    professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name='case_messages')
    message = models.TextField()
    admin_response = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
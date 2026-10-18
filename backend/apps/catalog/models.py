from django.db import models
from apps.authentication.models import ProfessionalProfile

class HomeZone(models.Model):
    """Zona del hogar (ej: Cocina, Baño, Jardín, Instalación Eléctrica General)."""
    name = models.CharField('Nombre de la zona', max_length=100, unique=True)
    description = models.TextField('Descripción', blank=True)

    class Meta:
        verbose_name = 'Zona del Hogar'
        verbose_name_plural = 'Zonas del Hogar'

    def __str__(self):
        return self.name


class TradeCategory(models.Model):
    """Oficio o categoría general (ej: Electricidad, Gasfitería, Cerrajería)."""
    name = models.CharField('Nombre del oficio', max_length=100, unique=True)
    home_zones = models.ManyToManyField(
        HomeZone, 
        related_name='trade_categories',
        verbose_name='Zonas asociadas'
    )
    keywords = models.TextField(
        'Palabras clave',
        help_text='Términos separados por comas para búsqueda semántica (ej: calefont, fuga, enchufe, llave)'
    )

    class Meta:
        verbose_name = 'Categoría de Oficio'
        verbose_name_plural = 'Categorías de Oficios'

    def __str__(self):
        return self.name


class Specialty(models.Model):
    """Sub-especialidad técnica (ej: Instalador SEC Clase B, Destape de cañerías)."""
    category = models.ForeignKey(
        TradeCategory, 
        on_delete=models.CASCADE, 
        related_name='specialties',
        verbose_name='Oficio'
    )
    name = models.CharField('Nombre de especialidad', max_length=120)
    professionals = models.ManyToManyField(
        ProfessionalProfile,
        related_name='specialties',
        blank=True,
        verbose_name='Profesionales calificados'
    )

    class Meta:
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Especialidades'

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ProfessionalTrade(models.Model):
    professional = models.ForeignKey(ProfessionalProfile, on_delete=models.CASCADE, related_name='trades')
    category = models.ForeignKey(TradeCategory, on_delete=models.PROTECT, related_name='professional_trades')
    years_experience = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)
    certification = models.FileField(upload_to='certifications/', blank=True)
    certification_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('professional', 'category'), name='unique_active_trade_category')]
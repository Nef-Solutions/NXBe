from django.db.models import BooleanField, Q
from django.db import connection
from django.db.models.expressions import RawSQL
from rest_framework.exceptions import ValidationError
from apps.authentication.models import ProfessionalProfile

class ProfessionalSearchService:
    @staticmethod
    def search(
        keyword: str = None, 
        zone_id: int = None, 
        category_id: int = None,
        specialty_id: int = None,
        commune: str = None,
        latitude: str = None,
        longitude: str = None,
        radius: str = None,
    ):
        """
        Reglas de negocio (Épica 002):
        1. Solo profesionales con perfil APROBADO son visibles.
        2. Los filtros por categoría y zona del hogar son opcionales y aditivos.
        3. La búsqueda por texto plano busca en nombre, apellido, especialidad y keywords.
        4. Consultas 100% parametrizadas vía ORM (evita SQL Injection).
        """
        # Regla 1: Solo verificados
        qs = ProfessionalProfile.objects.filter(
            verification_status=ProfessionalProfile.VerificationStatus.APPROVED
        ).select_related('user')

        # Regla 2: Filtrado por Zona del Hogar
        if zone_id:
            qs = qs.filter(specialties__category__home_zones__id=zone_id)

        # Regla 3: Filtrado por Oficio / Categoría
        active_trade = Q(trades__is_active=True) | Q(trades__isnull=True)

        if category_id:
            qs = qs.filter(specialties__category__id=category_id).filter(active_trade)

        if specialty_id:
            qs = qs.filter(specialties__id=specialty_id).filter(active_trade)

        if commune:
            qs = qs.filter(coverage_communes__contains=[commune])

        if any(value is not None for value in (latitude, longitude, radius)):
            if connection.vendor != 'postgresql':
                raise ValidationError('La búsqueda por radio requiere PostgreSQL con PostGIS.')
            if latitude is None or longitude is None or radius is None:
                raise ValidationError('latitude, longitude y radius son obligatorios para buscar por radio.')
            try:
                latitude_value = float(latitude)
                longitude_value = float(longitude)
                radius_value = int(radius)
            except (TypeError, ValueError):
                raise ValidationError('Las coordenadas y el radio deben tener un formato válido.')
            if not -90 <= latitude_value <= 90 or not -180 <= longitude_value <= 180:
                raise ValidationError('Las coordenadas están fuera de rango.')
            if radius_value not in (1000, 5000, 10000):
                raise ValidationError('El radio debe ser 1000, 5000 o 10000 metros.')
            qs = qs.annotate(
                within_radius=RawSQL(
                    """
                    ST_DWithin(
                        ST_SetSRID(ST_MakePoint(service_longitude, service_latitude), 4326)::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s
                    )
                    """,
                    (longitude_value, latitude_value, radius_value),
                    output_field=BooleanField(),
                )
            ).filter(within_radius=True)

        # Regla 4: Búsqueda por palabra clave
        if keyword:
            term = keyword.strip()
            if term:
                qs = qs.filter(
                    Q(user__first_name__icontains=term) |
                    Q(user__last_name__icontains=term) |
                    Q(specialties__name__icontains=term) |
                    Q(specialties__category__name__icontains=term) |
                    Q(specialties__category__keywords__icontains=term)
                )

        return qs.filter(active_trade).distinct()
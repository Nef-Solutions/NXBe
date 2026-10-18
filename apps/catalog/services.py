from django.db.models import Q
from apps.authentication.models import ProfessionalProfile

class ProfessionalSearchService:
    @staticmethod
    def search(
        keyword: str = None, 
        zone_id: int = None, 
        category_id: int = None
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
        if category_id:
            qs = qs.filter(specialties__category__id=category_id)

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

        return qs.distinct()
from django.test import TestCase
from apps.authentication.models import User, ProfessionalProfile
from apps.catalog.models import HomeZone, TradeCategory, Specialty
from apps.catalog.services import ProfessionalSearchService

class CatalogSearchTestCase(TestCase):
    def setUp(self):
        # 1. Crear zonas y categorías
        self.zona_cocina = HomeZone.objects.create(name="Cocina")
        self.cat_gasfiteria = TradeCategory.objects.create(
            name="Gasfitería", 
            keywords="cañerías, fugas, calefont, llave"
        )
        self.cat_gasfiteria.home_zones.add(self.zona_cocina)
        
        self.especialidad_fugas = Specialty.objects.create(
            category=self.cat_gasfiteria,
            name="Reparación de Fugas"
        )

        # 2. Profesional Verificado
        self.user_aprobado = User.objects.create_user(
            username="pro_juan",
            email="juan@overol.cl",
            password="PasswordSegura123!",
            first_name="Juan",
            last_name="Pérez",
            role=User.Role.PROFESSIONAL
        )
        self.pro_aprobado = ProfessionalProfile.objects.create(
            user=self.user_aprobado,
            rut="11111111-1",
            verification_status=ProfessionalProfile.VerificationStatus.APPROVED
        )
        self.especialidad_fugas.professionals.add(self.pro_aprobado)

        # 3. Profesional Pendiente (No debe salir en las búsquedas)
        self.user_pendiente = User.objects.create_user(
            username="pro_pedro",
            email="pedro@overol.cl",
            password="PasswordSegura123!",
            first_name="Pedro",
            last_name="González",
            role=User.Role.PROFESSIONAL
        )
        self.pro_pendiente = ProfessionalProfile.objects.create(
            user=self.user_pendiente,
            rut="22222222-2",
            verification_status=ProfessionalProfile.VerificationStatus.PENDING
        )
        self.especialidad_fugas.professionals.add(self.pro_pendiente)

    def test_search_only_returns_approved_professionals(self):
        """Regla: Solo perfiles verificados deben aparecer en la búsqueda."""
        results = ProfessionalSearchService.search(category_id=self.cat_gasfiteria.id)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().user.email, "juan@overol.cl")

    def test_search_by_home_zone(self):
        """Regla: Filtrar por zona del hogar."""
        results = ProfessionalSearchService.search(zone_id=self.zona_cocina.id)
        self.assertEqual(results.count(), 1)

    def test_search_by_keyword(self):
        """Regla: Búsqueda por término libre (ej: 'calefont')."""
        results = ProfessionalSearchService.search(keyword="calefont")
        self.assertEqual(results.count(), 1)

    def test_search_sqli_resilience(self):
        """Regla: Palabras clave con caracteres SQL no deben romper la búsqueda."""
        results = ProfessionalSearchService.search(keyword="' OR 1=1; --")
        self.assertEqual(results.count(), 0)
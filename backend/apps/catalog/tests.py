from django.db import connection
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from apps.authentication.models import User, ProfessionalProfile
from apps.catalog.models import HomeZone, TradeCategory, Specialty
from apps.catalog.services import ProfessionalSearchService
from rest_framework.test import APIClient

class CatalogSearchTestCase(TestCase):
    def setUp(self):
        # 1. Crear zonas y categorías
        self.zona_cocina = HomeZone.objects.create(name="Cocina")
        self.cat_gasfiteria = TradeCategory.objects.create(
            name="Gasfiteria - pruebas",
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

    def test_search_endpoint_is_available_under_professionals_prefix(self):
        response = APIClient().get(
            '/api/professionals/search/',
            {'keyword': 'fugas', 'commune': '', 'category_id': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.pro_aprobado.id)

    def test_search_sqli_resilience(self):
        """Regla: Palabras clave con caracteres SQL no deben romper la búsqueda."""
        results = ProfessionalSearchService.search(keyword="' OR 1=1; --")
        self.assertEqual(results.count(), 0)

    def test_search_filters_specialty_and_commune(self):
        self.pro_aprobado.coverage_communes = ['Maipu']
        self.pro_aprobado.save(update_fields=['coverage_communes'])
        results = ProfessionalSearchService.search(
            specialty_id=self.especialidad_fugas.id,
            commune='Maipu',
        )
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.pro_aprobado)

    def test_radio_search_accepts_only_supported_radii(self):
        with self.assertRaises(ValidationError):
            ProfessionalSearchService.search(latitude='-33.5', longitude='-70.6', radius='2000')

    def test_radio_search_requires_postgis_or_reports_clear_error(self):
        if connection.vendor == 'postgresql':
            results = ProfessionalSearchService.search(
                latitude='-33.5', longitude='-70.6', radius='1000'
            )
            self.assertEqual(results.count(), 0)
        else:
            with self.assertRaisesMessage(ValidationError, 'PostgreSQL con PostGIS'):
                ProfessionalSearchService.search(
                    latitude='-33.5', longitude='-70.6', radius='1000'
                )

    def test_professional_can_update_availability_and_create_trade(self):
        client = APIClient()
        client.force_authenticate(self.user_aprobado)
        response = client.patch(
            '/api/professionals/me/availability/',
            {
                'work_days': ['lunes'],
                'work_start': '09:00',
                'work_end': '18:00',
                'coverage_communes': ['Maipu'],
                'latitude': '-33.51000',
                'longitude': '-70.75000',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.pro_aprobado.refresh_from_db()
        self.assertEqual(self.pro_aprobado.coverage_communes, ['Maipu'])
        response = client.post(
            '/api/professionals/me/trades/',
            {'category_id': self.cat_gasfiteria.pk, 'years_experience': 4, 'description': 'Mantenciones'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.pro_aprobado.trades.count(), 1)

    def test_client_cannot_manage_professional_availability(self):
        client_user = User.objects.create_user(
            username='catalog_client', email='catalog.client@overol.cl',
            password='PasswordSegura123!', role=User.Role.CLIENT,
        )
        client = APIClient()
        client.force_authenticate(client_user)
        response = client.get('/api/professionals/me/availability/')
        self.assertEqual(response.status_code, 403)
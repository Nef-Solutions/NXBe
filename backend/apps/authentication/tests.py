from django.test import TestCase
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from apps.authentication.models import User, ProfessionalProfile
from apps.authentication.validators import sanitize_person_name, validate_rut_chileno

class UserSecurityAndBusinessRulesTestCase(TestCase):

    def test_sanitize_bernardo_ohiggins_complex_case(self):
        """Prueba que el caso 'Bernardo O’higgin’s . ' se limpie y normalice correctamente."""
        raw_name = "Bernardo O’higgin’s . "
        sanitized = sanitize_person_name(raw_name)
        self.assertEqual(sanitized, "Bernardo O'higgin's")

    def test_sqli_payload_rejection(self):
        """Prueba que intentos directos de inyección SQL sean rechazados por validación."""
        malicious_input = "Bernardo'; DROP TABLE users;--"
        with self.assertRaises(ValidationError):
            sanitize_person_name(malicious_input)

    def test_orm_escapes_quotes_safely(self):
        """
        Prueba que el ORM de Django maneje parámetros con apóstrofes de forma segura,
        sin romper la consulta SQL subyacente.
        """
        user = User.objects.create_user(
            username="bernardo_ohiggins",
            email="bernardo@overol.cl",
            password="PasswordSegura123!",
            first_name="Bernardo O’higgin’s . ",
            last_name="Riquelme",
            role=User.Role.PROFESSIONAL
        )
        # La consulta parametrizada busca exactamente la cadena limpia y escapada
        found_user = User.objects.filter(first_name="Bernardo O'higgin's").first()
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.first_name, "Bernardo O'higgin's")

    def test_validate_rut_modulo_11(self):
        """Prueba la validación y formato canónico del RUT."""
        rut_valido = "11.111.111-1"
        self.assertEqual(validate_rut_chileno(rut_valido), "11111111-1")

        rut_invalido = "11.111.111-9"
        with self.assertRaises(ValidationError):
            validate_rut_chileno(rut_invalido)


class JwtAuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='jwt_user',
            email='jwt@overol.cl',
            password='PasswordSegura123!',
            first_name='JWT',
            last_name='User',
        )

    def test_obtain_refresh_and_use_access_token(self):
        response = self.client.post('/api/auth/token/', {
            'email': 'jwt@overol.cl',
            'password': 'PasswordSegura123!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        refresh_response = self.client.post('/api/auth/token/refresh/', {
            'refresh': response.data['refresh'],
        }, format='json')
        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn('access', refresh_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile_response = self.client.get('/api/auth/me/')
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data['email'], 'jwt@overol.cl')

    def test_token_rejects_deactivated_account(self):
        self.user.account_status = User.AccountStatus.DEACTIVATED
        self.user.is_active = False
        self.user.save(update_fields=['account_status', 'is_active'])
        response = self.client.post('/api/auth/token/', {
            'email': 'jwt@overol.cl',
            'password': 'PasswordSegura123!',
        }, format='json')
        self.assertEqual(response.status_code, 401)
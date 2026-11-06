from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from apps.authentication.models import User, ProfessionalProfile
from apps.authentication.validators import sanitize_person_name, validate_rut_chileno
from apps.catalog.models import TradeCategory

class UserSecurityAndBusinessRulesTestCase(TestCase):

    def test_professional_registration_creates_required_profile_data(self):
        category, _ = TradeCategory.objects.get_or_create(
            name='Gasfitería',
            defaults={'keywords': 'fuga,cañería'},
        )
        response = APIClient().post('/api/auth/register/', {
            'email': 'professional.registration@test.cl',
            'first_name': 'Profesional',
            'last_name': 'Prueba',
            'phone': '+56912345678',
            'rut': '11111111-1',
            'address': 'Dirección 123',
            'commune': 'Santiago',
            'role': User.Role.PROFESSIONAL,
            'password': 'PasswordSegura123!',
            'privacy_policy_accepted': True,
            'privacy_policy_version': '2026-10',
            'professional_profile': {
                'coverage_communes': ['Santiago'],
                'categories': [{
                    'category': category.name,
                    'years_experience': 3,
                }],
            },
        }, format='json')

        self.assertEqual(response.status_code, 201)
        profile = ProfessionalProfile.objects.get(user__email='professional.registration@test.cl')
        self.assertEqual(list(profile.coverage_communes), ['Santiago'])
        self.assertEqual(profile.trades.get().category, category)

    def test_local_dashboard_is_staff_only_and_renders(self):
        client = Client()
        self.assertEqual(client.get('/local-dashboard/').status_code, 302)
        admin = User.objects.create_user(
            username='dashboard_admin',
            email='dashboard.admin@test.cl',
            password='PasswordSegura123!',
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.assertTrue(client.login(email=admin.email, password='PasswordSegura123!'))
        response = client.get('/local-dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operar historias de usuario')
        self.assertContains(response, 'Django Admin')

    def test_local_dashboard_registers_and_selects_demo_actor(self):
        client = Client()
        admin = User.objects.create_user(
            username='dashboard_admin',
            email='dashboard.admin@test.cl',
            password='PasswordSegura123!',
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.assertTrue(client.login(email=admin.email, password='PasswordSegura123!'))
        response = client.post('/local-dashboard/', {
            'action': 'register',
            'role': User.Role.CLIENT,
            'email': 'dashboard.client@test.cl',
            'password': 'PasswordSegura123!',
            'first_name': 'Cliente',
            'last_name': 'Demo',
            'rut': '22222222-2',
            'phone': '999999999',
            'address': 'Dirección de prueba 1',
            'commune': 'Santiago',
        })
        self.assertEqual(response.status_code, 302)
        actor = User.objects.get(email='dashboard.client@test.cl')
        self.assertTrue(client.post('/local-dashboard/', {
            'action': 'select_actor',
            'actor_id': actor.pk,
        }).status_code, 302)
        self.assertEqual(client.session['local_actor_id'], actor.pk)

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

        rut_nulo = "00.000.000-0"
        with self.assertRaises(ValidationError):
            validate_rut_chileno(rut_nulo)


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


class AuthenticationBusinessRulesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='client_rules',
            email='rules@overol.cl',
            password='PasswordSegura123!',
            first_name='Regla',
            last_name='Cliente',
            rut='11111111-1',
            role=User.Role.CLIENT,
        )
        self.professional_user = User.objects.create_user(
            username='pro_rules',
            email='pro.rules@overol.cl',
            password='PasswordSegura123!',
            first_name='Pro',
            last_name='Reglas',
            rut='22222222-2',
            role=User.Role.PROFESSIONAL,
        )
        self.professional = ProfessionalProfile.objects.create(
            user=self.professional_user,
            rut='22222222-2',
            verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
        )

    def test_registration_requires_privacy_and_strong_password(self):
        payload = {
            'email': 'new@overol.cl',
            'first_name': 'Nuevo',
            'last_name': 'Cliente',
            'rut': '33333333-3',
            'password': '12345678',
            'role': User.Role.CLIENT,
            'privacy_policy_accepted': False,
            'privacy_policy_version': '2026.1',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('privacy_policy_accepted', response.data)

    def test_login_locks_after_three_failures_and_returns_retry_after(self):
        for _ in range(3):
            response = self.client.post('/api/auth/token/', {
                'email': self.user.email,
                'password': 'incorrecta',
            }, format='json')
            self.assertEqual(response.status_code, 401)
        response = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'PasswordSegura123!',
        }, format='json')
        self.assertEqual(response.status_code, 429)
        self.assertIn('retry_after', response.data)

    def test_profile_serializer_hides_sensitive_professional_data_for_client(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f'/api/catalog/professionals/{self.professional.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['rut'])
        self.assertIsNone(response.data['address'])
        self.assertNotIn('email', response.data)

    def test_admin_can_read_private_verification_document_only(self):
        document = SimpleUploadedFile('id.png', b'fake-image', content_type='image/png')
        self.professional.id_card_front = document
        self.professional.save()

        self.client.force_authenticate(self.user)
        forbidden = self.client.get(
            f'/api/admin/verifications/{self.professional.pk}/document/?side=front'
        )
        self.assertIn(forbidden.status_code, (401, 403))

        admin = User.objects.create_superuser(
            username='admin_rules',
            email='admin.rules@overol.cl',
            password='PasswordSegura123!',
        )
        admin.role = User.Role.ADMIN
        admin.save(update_fields=['role'])
        self.client.force_authenticate(admin)
        response = self.client.get(
            f'/api/admin/verifications/{self.professional.pk}/document/?side=front'
        )
        self.assertEqual(response.status_code, 200)

    def test_account_status_requires_reason_and_deactivated_account_cannot_login(self):
        admin = User.objects.create_superuser(
            username='admin_status',
            email='admin.status@overol.cl',
            password='PasswordSegura123!',
        )
        admin.role = User.Role.ADMIN
        admin.save(update_fields=['role'])
        self.client.force_authenticate(admin)
        response = self.client.post(
            f'/api/auth/admin/accounts/{self.user.pk}/status/',
            {'status': User.AccountStatus.DEACTIVATED},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            f'/api/auth/admin/accounts/{self.user.pk}/status/',
            {'status': User.AccountStatus.DEACTIVATED, 'reason': 'Solicitud del usuario'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(None)
        response = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'PasswordSegura123!',
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post('/api/auth/token/', {
            'email': self.user.email,
            'password': 'PasswordSegura123!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        refresh = response.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        logout_response = self.client.post('/api/auth/logout/', {'refresh': refresh}, format='json')
        self.assertEqual(logout_response.status_code, 204)
        refresh_response = self.client.post('/api/auth/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(refresh_response.status_code, 401)

    def test_admin_verification_decision_notifies_and_audits(self):
        from apps.visits.models import AdminAuditLog, Notification

        admin = User.objects.create_superuser(
            username='admin_verification',
            email='admin.verification@overol.cl',
            password='PasswordSegura123!',
        )
        admin.role = User.Role.ADMIN
        admin.save(update_fields=['role'])
        self.client.force_authenticate(admin)
        response = self.client.post(
            f'/api/auth/verification/{self.professional.pk}/reject/',
            {'reason': 'Documento ilegible'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], ProfessionalProfile.VerificationStatus.REJECTED)
        self.assertTrue(Notification.objects.filter(recipient=self.professional_user).exists())
        self.assertTrue(AdminAuditLog.objects.filter(target_id=self.professional.pk).exists())
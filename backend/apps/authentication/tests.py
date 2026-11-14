from datetime import timedelta
from io import BytesIO
import re
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from apps.authentication.models import PasswordResetCode, User, ProfessionalProfile
from apps.authentication.storage import private_verification_storage
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
            subscription_expires_at=timezone.now() + timedelta(days=30),
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


class VerificationDocumentUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='document_professional',
            email='document.professional@overol.cl',
            password='PasswordSegura123!',
            first_name='Documento',
            last_name='Profesional',
            rut='11111111-1',
            role=User.Role.PROFESSIONAL,
        )
        self.profile = ProfessionalProfile.objects.create(
            user=self.user,
            rut=self.user.rut,
        )
        self.client.force_authenticate(self.user)

        self.storage = private_verification_storage
        self.previous_location = self.storage._location
        self.previous_location_cache = self.storage.__dict__.pop('location', None)
        self.previous_base_location_cache = self.storage.__dict__.pop('base_location', None)
        self.temp_storage = tempfile.TemporaryDirectory()
        self.storage._location = self.temp_storage.name

    def tearDown(self):
        for field_name in ('id_card_front', 'id_card_back'):
            uploaded = getattr(self.profile, field_name)
            if uploaded:
                uploaded.storage.delete(uploaded.name)
        self.temp_storage.cleanup()
        self.storage._location = self.previous_location
        self.storage.__dict__.pop('location', None)
        self.storage.__dict__.pop('base_location', None)
        if self.previous_location_cache is not None:
            self.storage.__dict__['location'] = self.previous_location_cache
        if self.previous_base_location_cache is not None:
            self.storage.__dict__['base_location'] = self.previous_base_location_cache

    @staticmethod
    def make_image(name, image_format='PNG'):
        content = BytesIO()
        Image.new('RGB', (12, 12), color='blue').save(content, format=image_format)
        return SimpleUploadedFile(
            name,
            content.getvalue(),
            content_type=f'image/{image_format.lower()}',
        )

    @staticmethod
    def make_pdf(name='id.pdf'):
        return SimpleUploadedFile(
            name,
            b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n',
            content_type='application/pdf',
        )

    def test_professional_can_upload_each_document_and_query_upload_state(self):
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': self.make_image('front.png')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['verification_status'], 'PENDING')
        self.assertEqual(response.data['documents'], {
            'front_uploaded': True,
            'back_uploaded': False,
        })
        status_response = self.client.get('/api/auth/verification/documents/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['documents'], response.data['documents'])
        self.assertNotIn('id_card_front', status_response.data)

        self.profile.refresh_from_db()
        self.profile.verification_status = ProfessionalProfile.VerificationStatus.APPROVED
        self.profile.save(update_fields=['verification_status'])
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_back': self.make_image('back.jpg', 'JPEG')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['verification_status'], 'PENDING')
        self.assertEqual(response.data['documents'], {
            'front_uploaded': True,
            'back_uploaded': True,
        })

    def test_document_upload_rejects_empty_or_non_image_payload(self):
        empty_response = self.client.post(
            '/api/auth/verification/documents/',
            {},
            format='multipart',
        )
        self.assertEqual(empty_response.status_code, 400)

        invalid_response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': SimpleUploadedFile(
                'fake.png',
                b'not an image',
                content_type='image/png',
            )},
            format='multipart',
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.id_card_front)

    def test_document_upload_rejects_files_over_five_megabytes_before_decoding(self):
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': SimpleUploadedFile(
                'oversized.png',
                b'x' * (5 * 1024 * 1024 + 1),
                content_type='image/png',
            )},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('5 MB', str(response.data['id_card_front']))

    def test_professional_can_upload_pdf_and_admin_receives_private_attachment(self):
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': self.make_pdf()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['documents']['front_uploaded'])

        admin = User.objects.create_superuser(
            username='pdf_document_admin',
            email='pdf.document.admin@overol.cl',
            password='PasswordSegura123!',
        )
        admin.role = User.Role.ADMIN
        admin.save(update_fields=['role'])
        self.client.force_authenticate(admin)
        download = self.client.get(
            f'/api/admin/verifications/{self.profile.pk}/document/?side=front'
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download['Content-Type'], 'application/pdf')
        self.assertTrue(download['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(b''.join(download.streaming_content), self.make_pdf().read())

    def test_document_upload_rejects_pdf_signature_with_wrong_extension(self):
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': self.make_pdf('id.png')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_only_professional_can_upload_documents(self):
        client_user = User.objects.create_user(
            username='document_client',
            email='document.client@overol.cl',
            password='PasswordSegura123!',
            first_name='Cliente',
            last_name='Documento',
            rut='22222222-2',
            role=User.Role.CLIENT,
        )
        self.client.force_authenticate(client_user)
        response = self.client.post(
            '/api/auth/verification/documents/',
            {'id_card_front': self.make_image('front.png')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_approve_before_both_documents_are_uploaded(self):
        admin = User.objects.create_superuser(
            username='document_admin',
            email='document.admin@overol.cl',
            password='PasswordSegura123!',
        )
        admin.role = User.Role.ADMIN
        admin.save(update_fields=['role'])
        self.client.force_authenticate(admin)
        response = self.client.post(
            f'/api/auth/verification/{self.profile.pk}/approve/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 400)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class PasswordResetApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='password_reset_user',
            email='password.reset@overol.cl',
            password='PasswordSegura123!',
            first_name='Recuperar',
            last_name='Cuenta',
            rut='11111111-1',
        )

    def request_code(self, email=None):
        response = self.client.post(
            '/api/auth/password/reset/',
            {'email': email or self.user.email},
            format='json',
        )
        return response

    @staticmethod
    def emailed_code():
        match = re.search(r'(?<!\d)\d{6}(?!\d)', mail.outbox[-1].body)
        if not match:
            raise AssertionError('The recovery email did not contain a six-digit code.')
        return match.group()

    def test_reset_request_returns_generic_response_and_sends_code(self):
        response = self.request_code()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        code = self.emailed_code()
        self.assertRegex(code, r'^\d{6}$')
        reset = PasswordResetCode.objects.get(user=self.user)
        self.assertTrue(reset.code_hash.startswith('pbkdf2_'))
        self.assertNotEqual(reset.code_hash, code)
        self.assertEqual(self.request_code().status_code, 202)
        self.assertEqual(len(mail.outbox), 1)

        unknown_response = self.request_code('unknown@overol.cl')
        self.assertEqual(unknown_response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)

    def test_valid_code_changes_password_revokes_refresh_and_cannot_be_reused(self):
        token_response = self.client.post(
            '/api/auth/token/',
            {'email': self.user.email, 'password': 'PasswordSegura123!'},
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(self.request_code().status_code, 202)
        code = self.emailed_code()

        response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {
                'email': self.user.email,
                'code': code,
                'new_password': 'BrandNewSecurePass890!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewSecurePass890!'))
        refresh_response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': token_response.data['refresh']},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, 401)

        replay_response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {
                'email': self.user.email,
                'code': code,
                'new_password': 'AnotherSecurePass890!',
            },
            format='json',
        )
        self.assertEqual(replay_response.status_code, 400)

    def test_reset_confirmation_rejects_invalid_code_and_weak_password(self):
        self.assertEqual(self.request_code().status_code, 202)
        code = self.emailed_code()
        response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {
                'email': self.user.email,
                'code': '000000' if code != '000000' else '000001',
                'new_password': 'BrandNewSecurePass890!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

        weak_password_response = self.client.post(
            '/api/auth/password/reset/confirm/',
            {
                'email': self.user.email,
                'code': code,
                'new_password': 'short',
            },
            format='json',
        )
        self.assertEqual(weak_password_response.status_code, 400)
        self.assertTrue(self.user.check_password('PasswordSegura123!'))

    def test_reset_code_expires_and_is_invalidated_after_five_wrong_attempts(self):
        self.assertEqual(self.request_code().status_code, 202)
        code = self.emailed_code()
        reset = PasswordResetCode.objects.get(user=self.user)
        reset.expires_at = timezone.now() - timedelta(seconds=1)
        reset.save(update_fields=['expires_at'])
        expired = self.client.post(
            '/api/auth/password/reset/confirm/',
            {
                'email': self.user.email,
                'code': code,
                'new_password': 'BrandNewSecurePass890!',
            },
            format='json',
        )
        self.assertEqual(expired.status_code, 400)

        PasswordResetCode.objects.filter(pk=reset.pk).update(
            created_at=timezone.now() - timedelta(minutes=2),
        )
        self.assertEqual(self.request_code().status_code, 202)
        reset = PasswordResetCode.objects.get(user=self.user)
        code = self.emailed_code()
        wrong_code = '000000' if code != '000000' else '000001'
        for _ in range(5):
            rejected = self.client.post(
                '/api/auth/password/reset/confirm/',
                {
                    'email': self.user.email,
                    'code': wrong_code,
                    'new_password': 'BrandNewSecurePass890!',
                },
                format='json',
            )
            self.assertEqual(rejected.status_code, 400)
        reset.refresh_from_db()
        self.assertIsNotNone(reset.consumed_at)
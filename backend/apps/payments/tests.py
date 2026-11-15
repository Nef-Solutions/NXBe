from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.authentication.models import ProfessionalProfile, User
from apps.catalog.models import Specialty, TradeCategory
from apps.visits.models import VisitRequest
from .models import PaymentTransaction, ProfessionalSubscriptionPlan
from .services import _add_months, token_digest


class PaymentApiTests(APITestCase):
    def setUp(self):
        self.plan = ProfessionalSubscriptionPlan.objects.get(code='professional-monthly')
        self.client_user = User.objects.create_user(
            username='payment-client',
            email='payment.client@overol.cl',
            password='PasswordSegura123!',
            role=User.Role.CLIENT,
        )
        self.professional_user = User.objects.create_user(
            username='payment-pro',
            email='payment.pro@overol.cl',
            password='PasswordSegura123!',
            role=User.Role.PROFESSIONAL,
        )
        self.professional = ProfessionalProfile.objects.create(
            user=self.professional_user,
            rut='11111111-1',
            verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
            visit_fee=15000,
        )
        category = TradeCategory.objects.create(name='Gasfitería pagos', keywords='fuga')
        self.specialty = Specialty.objects.create(category=category, name='Reparaciones')
        self.visit = VisitRequest.objects.create(
            client=self.client_user,
            professional=self.professional,
            specialty=self.specialty,
            problem_description='Filtración de agua',
            visit_address='Calle 123',
            status=VisitRequest.Status.ACCEPTED,
        )
        self.client.force_authenticate(self.client_user)

    @patch('apps.payments.services.webpay_transaction')
    def test_professional_can_start_monthly_subscription_payment(self, transaction_factory):
        transbank = Mock()
        transbank.create.return_value = {
            'token': 'subscription-sandbox-token',
            'url': 'https://sandbox.transbank.cl',
        }
        transaction_factory.return_value = transbank
        self.client.force_authenticate(self.professional_user)

        response = self.client.post(
            '/api/payments/professional-subscription/transbank/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['amount'], '10000')
        self.assertEqual(response.data['environment'], 'sandbox')
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.professional, self.professional)
        self.assertIsNone(payment.visit)
        self.assertEqual(payment.amount, self.plan.amount)
        self.assertEqual(payment.subscription_plan, self.plan)
        self.assertEqual(payment.subscription_duration_months, self.plan.duration_months)
        self.assertEqual(payment.token_hash, token_digest('subscription-sandbox-token'))

    def test_client_cannot_start_professional_subscription(self):
        response = self.client.post(
            '/api/payments/professional-subscription/transbank/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_professional_can_check_subscription_status(self):
        self.client.force_authenticate(self.professional_user)
        response = self.client.get('/api/payments/professional-subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'INACTIVE')
        self.assertEqual(response.data['amount'], str(self.plan.amount))
        self.assertEqual(response.data['plan']['duration_months'], 1)
        self.assertIsNone(response.data['expires_at'])

    @patch('apps.payments.services.webpay_transaction')
    def test_subscription_payment_uses_active_plan_price_and_duration(self, transaction_factory):
        self.plan.amount = 17500
        self.plan.duration_months = 3
        self.plan.save(update_fields=['amount', 'duration_months', 'updated_at'])
        transbank = Mock()
        transbank.create.return_value = {
            'token': 'custom-plan-token',
            'url': 'https://sandbox.transbank.cl',
        }
        transaction_factory.return_value = transbank
        self.client.force_authenticate(self.professional_user)

        response = self.client.post(
            '/api/payments/professional-subscription/transbank/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['amount'], '17500')
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.subscription_plan, self.plan)
        self.assertEqual(payment.subscription_duration_months, 3)
        transbank.create.assert_called_once()
        self.assertEqual(transbank.create.call_args.args[2], 17500.0)

        self.plan.duration_months = 6
        self.plan.save(update_fields=['duration_months', 'updated_at'])
        transbank.commit.return_value = {
            'buy_order': payment.buy_order,
            'session_id': payment.session_id,
            'amount': payment.amount,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        expected_expiration = _add_months(timezone.now(), 3)
        self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'custom-plan-token'},
            format='multipart',
        )
        payment.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.AUTHORIZED)
        self.assertGreaterEqual(
            self.professional.subscription_expires_at,
            expected_expiration,
        )

    def test_subscription_endpoints_report_unavailable_without_an_active_plan(self):
        self.plan.is_active = False
        self.plan.save(update_fields=['is_active', 'updated_at'])
        self.client.force_authenticate(self.professional_user)

        status_response = self.client.get('/api/payments/professional-subscription/')
        create_response = self.client.post(
            '/api/payments/professional-subscription/transbank/',
            {},
            format='json',
        )

        self.assertEqual(status_response.status_code, 503)
        self.assertEqual(create_response.status_code, 409)

    @patch('apps.payments.services.webpay_transaction')
    def test_initiates_sandbox_payment_using_professional_visit_fee(self, transaction_factory):
        transbank = Mock()
        transbank.create.return_value = {'token': 'sandbox-token', 'url': 'https://sandbox.transbank.cl'}
        transaction_factory.return_value = transbank

        response = self.client.post(
            f'/api/payments/visits/{self.visit.pk}/transbank/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['amount'], '15000')
        self.assertEqual(response.data['environment'], 'sandbox')
        self.assertEqual(
            PaymentTransaction.objects.get().token_hash,
            token_digest('sandbox-token'),
        )

    def test_payment_requires_accepted_visit(self):
        self.visit.status = VisitRequest.Status.PENDING
        self.visit.save(update_fields=['status'])

        response = self.client.post(
            f'/api/payments/visits/{self.visit.pk}/transbank/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 409)

    @patch('apps.payments.services.webpay_transaction')
    def test_expired_pending_payment_can_be_retried(self, transaction_factory):
        old_payment = PaymentTransaction.objects.create(
            visit=self.visit,
            payer=self.client_user,
            amount=15000,
            buy_order='ov-expired-order',
            session_id='ov-expired-session',
        )
        PaymentTransaction.objects.filter(pk=old_payment.pk).update(
            created_at=timezone.now() - timedelta(hours=1),
        )
        transbank = Mock()
        transbank.create.return_value = {'token': 'new-token', 'url': 'https://sandbox.transbank.cl'}
        transaction_factory.return_value = transbank

        response = self.client.post(
            f'/api/payments/visits/{self.visit.pk}/transbank/',
            {},
            format='json',
        )

        old_payment.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(old_payment.status, PaymentTransaction.Status.FAILED)
        self.assertEqual(PaymentTransaction.objects.filter(visit=self.visit).count(), 2)

    def test_another_client_cannot_access_payment_status(self):
        other_user = User.objects.create_user(
            username='other-client',
            email='other.client@overol.cl',
            password='PasswordSegura123!',
            role=User.Role.CLIENT,
        )
        self.client.force_authenticate(other_user)
        response = self.client.get(f'/api/payments/visits/{self.visit.pk}/')
        self.assertEqual(response.status_code, 404)

    @patch('apps.payments.services.webpay_transaction')
    @override_settings(PAYMENT_RESULT_URL='http://localhost:3000/payment-result')
    def test_return_marks_matching_transaction_authorized(self, transaction_factory):
        payment = PaymentTransaction.objects.create(
            visit=self.visit,
            payer=self.client_user,
            amount=15000,
            buy_order='ov-test-order',
            session_id='ov-test-session',
            token_hash=token_digest('sandbox-token'),
        )
        transbank = Mock()
        transbank.commit.return_value = {
            'buy_order': payment.buy_order,
            'session_id': payment.session_id,
            'amount': 15000,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        transaction_factory.return_value = transbank

        response = self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'sandbox-token'},
            format='multipart',
        )

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.AUTHORIZED)
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=authorized', response['Location'])

    @patch('apps.payments.services.webpay_transaction')
    @override_settings(PAYMENT_RESULT_URL='http://localhost:3000/payment-result')
    def test_get_return_confirms_subscription_from_query_string(self, transaction_factory):
        payment = PaymentTransaction.objects.create(
            professional=self.professional,
            payer=self.professional_user,
            amount=self.plan.amount,
            buy_order='ov-get-subscription',
            session_id='ov-get-subscription-session',
            token_hash=token_digest('get-subscription-token'),
        )
        transbank = Mock()
        transbank.commit.return_value = {
            'buy_order': payment.buy_order,
            'session_id': payment.session_id,
            'amount': self.plan.amount,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        transaction_factory.return_value = transbank

        response = self.client.get(
            '/api/payments/transbank/return/',
            {'token_ws': 'get-subscription-token'},
        )

        payment.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.AUTHORIZED)
        self.assertIsNotNone(self.professional.subscription_expires_at)
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=authorized', response['Location'])
        self.assertIn(
            f'professional_profile_id={self.professional.pk}',
            response['Location'],
        )
        transbank.commit.assert_called_once_with('get-subscription-token')

    @override_settings(PAYMENT_RESULT_URL='http://localhost:3000/payment-result')
    def test_get_return_cancels_payment_from_query_string(self):
        payment = PaymentTransaction.objects.create(
            visit=self.visit,
            payer=self.client_user,
            amount=15000,
            buy_order='ov-cancelled-order',
            session_id='ov-cancelled-session',
            token_hash=token_digest('cancelled-token'),
        )

        response = self.client.get(
            '/api/payments/transbank/return/',
            {
                'TBK_TOKEN': 'cancelled-token',
                'TBK_ORDEN_COMPRA': payment.buy_order,
            },
        )

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.REJECTED)
        self.assertEqual(response.status_code, 302)
        self.assertIn('status=cancelled', response['Location'])
        self.assertIn(f'visit_id={self.visit.pk}', response['Location'])

    @patch('apps.payments.services.webpay_transaction')
    @override_settings(PAYMENT_RESULT_URL='http://localhost:3000/payment-result')
    def test_authorized_subscription_payment_activates_one_month(self, transaction_factory):
        payment = PaymentTransaction.objects.create(
            professional=self.professional,
            payer=self.professional_user,
            amount=self.plan.amount,
            buy_order='ov-subscription-test',
            session_id='ov-subscription-session',
            token_hash=token_digest('subscription-token'),
        )
        transbank = Mock()
        transbank.commit.return_value = {
            'buy_order': payment.buy_order,
            'session_id': payment.session_id,
            'amount': self.plan.amount,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        transaction_factory.return_value = transbank
        now = timezone.now()

        response = self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'subscription-token'},
            format='multipart',
        )

        payment.refresh_from_db()
        self.professional.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.AUTHORIZED)
        self.assertGreaterEqual(self.professional.subscription_expires_at, _add_months(now, 1))
        self.assertIn('status=authorized', response['Location'])
        self.assertIn(
            f'professional_profile_id={self.professional.pk}',
            response['Location'],
        )
        first_expiration = self.professional.subscription_expires_at

        self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'subscription-token'},
            format='multipart',
        )
        self.professional.refresh_from_db()
        self.assertEqual(
            self.professional.subscription_expires_at,
            first_expiration,
        )
        transbank.commit.assert_called_once_with('subscription-token')

        renewal = PaymentTransaction.objects.create(
            professional=self.professional,
            payer=self.professional_user,
            amount=self.plan.amount,
            buy_order='ov-subscription-renewal',
            session_id='ov-subscription-renewal-session',
            token_hash=token_digest('subscription-renewal-token'),
        )
        transbank.commit.return_value = {
            'buy_order': renewal.buy_order,
            'session_id': renewal.session_id,
            'amount': self.plan.amount,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'subscription-renewal-token'},
            format='multipart',
        )
        self.professional.refresh_from_db()
        self.assertEqual(
            self.professional.subscription_expires_at,
            _add_months(first_expiration, 1),
        )
    @patch('apps.payments.services.webpay_transaction')
    @override_settings(PAYMENT_RESULT_URL='http://localhost:3000/payment-result')
    def test_return_rejects_mismatched_amount(self, transaction_factory):
        payment = PaymentTransaction.objects.create(
            visit=self.visit,
            payer=self.client_user,
            amount=15000,
            buy_order='ov-mismatched-order',
            session_id='ov-mismatched-session',
            token_hash=token_digest('other-token'),
        )
        transbank = Mock()
        transbank.commit.return_value = {
            'buy_order': payment.buy_order,
            'session_id': payment.session_id,
            'amount': 15001,
            'response_code': 0,
            'status': 'AUTHORIZED',
        }
        transaction_factory.return_value = transbank

        response = self.client.post(
            '/api/payments/transbank/return/',
            {'token_ws': 'other-token'},
            format='multipart',
        )

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertIn('status=error', response['Location'])

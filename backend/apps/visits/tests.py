from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.authentication.models import ProfessionalProfile, User
from apps.catalog.models import Specialty, TradeCategory

from .models import Notification, ProfessionalContent, Rating, SupportTicket, VisitRequest
from .serializers import RatingSerializer, VisitRequestSerializer
from .services import expire_pending_requests


class VisitLifecycleTestCase(TestCase):
	def setUp(self):
		self.client_user = User.objects.create_user(
			username='cliente', email='cliente@test.cl', password='PasswordSegura123!', role=User.Role.CLIENT
		)
		self.professional_user = User.objects.create_user(
			username='profesional', email='profesional@test.cl', password='PasswordSegura123!', role=User.Role.PROFESSIONAL
		)
		self.professional = ProfessionalProfile.objects.create(
			user=self.professional_user, rut='11111111-1', verification_status=ProfessionalProfile.VerificationStatus.APPROVED
		)
		category = TradeCategory.objects.create(name='Electricidad - pruebas', keywords='enchufe, cable')
		self.specialty = Specialty.objects.create(category=category, name='Instalaciones electricas - pruebas')
		self.specialty.professionals.add(self.professional)
		self.visit = VisitRequest.objects.create(
			client=self.client_user,
			professional=self.professional,
			specialty=self.specialty,
			problem_description='No funciona un enchufe',
			visit_address='Calle de prueba 123',
		)

	def test_visit_requires_both_confirmations(self):
		self.visit.accept()
		self.visit.finish_by_professional()
		self.assertEqual(self.visit.status, VisitRequest.Status.PROFESSIONAL_FINISHED)
		self.visit.confirm_by_client()
		self.assertEqual(self.visit.status, VisitRequest.Status.COMPLETED)

	def test_pending_visit_cannot_be_finished(self):
		with self.assertRaises(ValueError):
			self.visit.finish_by_professional()

	def test_rejection_requires_reason(self):
		with self.assertRaises(ValueError):
			self.visit.reject('')


class VisitBusinessRulesTestCase(TestCase):
	def setUp(self):
		self.api = APIClient()
		self.factory = APIRequestFactory()
		self.client_user = User.objects.create_user(
			username='client_api', email='client.api@test.cl',
			password='PasswordSegura123!', role=User.Role.CLIENT,
		)
		self.professional_user = User.objects.create_user(
			username='professional_api', email='professional.api@test.cl',
			password='PasswordSegura123!', role=User.Role.PROFESSIONAL,
		)
		self.professional = ProfessionalProfile.objects.create(
			user=self.professional_user, rut='11111111-1',
			verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
			work_days=['monday'], work_start='09:00', work_end='17:00',
			is_available=True, coverage_communes=['Maipu'],
		)
		category = TradeCategory.objects.create(name='Gasfiteria de visitas - pruebas', keywords='agua')
		self.specialty = Specialty.objects.create(category=category, name='Reparaciones - pruebas')
		self.specialty.professionals.add(self.professional)

	def build_visit_payload(self, date=None, visit_time='10:00 - 11:00'):
		return {
			'professional': self.professional.pk,
			'specialty': self.specialty.pk,
			'problem_description': 'Fuga de agua',
			'visit_date': date or (timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()) % 7 or 7)),
			'visit_time': visit_time,
			'commune': 'Maipu',
			'visit_address': 'Direccion de prueba 1',
		}

	def test_visit_rejects_day_and_time_outside_professional_schedule(self):
		next_tuesday = timezone.localdate() + timedelta(days=(8 - timezone.localdate().weekday()) % 7 or 7)
		day_payload = self.build_visit_payload(date=next_tuesday)
		request = self.factory.post('/api/requests/', day_payload, format='json')
		request.user = self.client_user
		serializer = VisitRequestSerializer(data=day_payload, context={'request': request})
		self.assertFalse(serializer.is_valid())
		self.assertIn('visit_date', serializer.errors)

		next_monday = timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()) % 7 or 7)
		payload = self.build_visit_payload(date=next_monday, visit_time='18:00 - 19:00')
		request = self.factory.post('/api/requests/', payload, format='json')
		request.user = self.client_user
		serializer = VisitRequestSerializer(data=payload, context={'request': request})
		self.assertFalse(serializer.is_valid())
		self.assertIn('visit_time', serializer.errors)

	def test_visit_creation_sets_thirty_day_expiry(self):
		next_monday = timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()) % 7 or 7)
		payload = self.build_visit_payload(date=next_monday)
		request = self.factory.post('/api/requests/', payload, format='json')
		request.user = self.client_user
		serializer = VisitRequestSerializer(data=payload, context={'request': request})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		visit = serializer.save()
		self.assertAlmostEqual(
			(visit.expires_at - visit.created_at).total_seconds(),
			timedelta(days=30).total_seconds(),
			delta=2,
		)

	def test_expiration_changes_status_and_notifies_once_per_run(self):
		visit = VisitRequest.objects.create(
			client=self.client_user, professional=self.professional, specialty=self.specialty,
			problem_description='Antigua', visit_address='Direccion',
		)
		VisitRequest.objects.filter(pk=visit.pk).update(
			created_at=timezone.now() - timedelta(days=31)
		)
		count = expire_pending_requests()
		visit.refresh_from_db()
		self.assertEqual(count, 1)
		self.assertEqual(visit.status, VisitRequest.Status.EXPIRED)
		self.assertEqual(Notification.objects.filter(related_visit=visit).count(), 1)
		self.assertEqual(expire_pending_requests(), 0)

	def completed_visit(self):
		visit = VisitRequest.objects.create(
			client=self.client_user, professional=self.professional, specialty=self.specialty,
			problem_description='Completada', visit_address='Direccion',
			status=VisitRequest.Status.PROFESSIONAL_FINISHED,
			professional_confirmed_at=timezone.now(),
		)
		visit.confirm_by_client()
		return visit

	def test_rating_is_allowed_once_within_thirty_days(self):
		visit = self.completed_visit()
		request = self.factory.post('/api/ratings/', {}, format='json')
		request.user = self.client_user
		payload = {
			'visit': visit.pk, 'quality': 5, 'punctuality': 4,
			'treatment': 5, 'comment': 'Buen servicio',
		}
		serializer = RatingSerializer(data=payload, context={'request': request})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		serializer.save()
		duplicate = RatingSerializer(data=payload, context={'request': request})
		self.assertFalse(duplicate.is_valid())
		self.assertIn('visit', duplicate.errors)

	def test_rating_expires_thirty_days_after_completion(self):
		visit = self.completed_visit()
		visit.completed_at = timezone.now() - timedelta(days=31)
		visit.save(update_fields=['completed_at'])
		request = self.factory.post('/api/ratings/', {}, format='json')
		request.user = self.client_user
		serializer = RatingSerializer(data={
			'visit': visit.pk, 'quality': 5, 'punctuality': 5, 'treatment': 5,
		}, context={'request': request})
		self.assertFalse(serializer.is_valid())
		self.assertIn('visit', serializer.errors)

	def test_contacts_are_hidden_before_acceptance_and_visible_only_to_parties_after(self):
		visit = VisitRequest.objects.create(
			client=self.client_user, professional=self.professional, specialty=self.specialty,
			problem_description='Contacto', visit_address='Direccion',
		)
		self.client_user.phone = '999999999'
		self.client_user.save(update_fields=['phone'])
		request = self.factory.get('/api/requests/')
		request.user = self.client_user
		serializer = VisitRequestSerializer(visit, context={'request': request})
		self.assertIsNone(serializer.data['phone'])
		visit.accept()
		serializer = VisitRequestSerializer(visit, context={'request': request})
		self.professional_user.phone = '888888888'
		self.professional_user.save(update_fields=['phone'])
		self.assertEqual(
			VisitRequestSerializer(visit, context={'request': request}).data['phone'],
			self.professional_user.phone,
		)
		outsider = User.objects.create_user(username='outsider', email='outsider@test.cl', password='PasswordSegura123!')
		request.user = outsider
		self.assertIsNone(VisitRequestSerializer(visit, context={'request': request}).data['phone'])

	def test_ticket_requires_owned_visit_and_admin_can_resolve_it(self):
		visit = VisitRequest.objects.create(
			client=self.client_user, professional=self.professional, specialty=self.specialty,
			problem_description='Ticket', visit_address='Direccion',
		)
		self.api.force_authenticate(self.client_user)
		response = self.api.post('/api/tickets/', {
			'visit': visit.pk, 'subject': 'Problema', 'description': 'x' * 501,
		}, format='json')
		self.assertEqual(response.status_code, 400)
		response = self.api.post('/api/tickets/', {
			'visit': visit.pk, 'subject': 'Problema', 'description': 'No puedo continuar',
		}, format='json')
		self.assertEqual(response.status_code, 201)
		ticket = SupportTicket.objects.get(pk=response.data['id'])
		admin = User.objects.create_superuser(
			username='visit_admin', email='visit.admin@test.cl',
			password='PasswordSegura123!',
		)
		admin.role = User.Role.ADMIN
		admin.save(update_fields=['role'])
		self.api.force_authenticate(admin)
		response = self.api.post(
			f'/api/tickets/{ticket.pk}/resolve/',
			{'response': 'Resuelto'},
			format='json',
		)
		self.assertEqual(response.status_code, 200)
		ticket.refresh_from_db()
		self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)

	def test_professional_center_is_role_protected_and_progress_is_recorded(self):
		content = ProfessionalContent.objects.create(
			title='Seguridad', module=ProfessionalContent.Module.SAFETY,
			url='https://example.com/seguridad', is_visible=True,
		)
		self.api.force_authenticate(self.client_user)
		self.assertEqual(self.api.get('/api/professional-center/content/').status_code, 403)
		self.api.force_authenticate(self.professional_user)
		response = self.api.get('/api/professional-center/content/')
		self.assertEqual(response.status_code, 200)
		response = self.api.post(
			'/api/professional-center/progress/',
			{'content': content.pk},
			format='json',
		)
		self.assertEqual(response.status_code, 201)

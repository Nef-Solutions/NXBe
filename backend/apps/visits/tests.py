from django.test import TestCase

from apps.authentication.models import ProfessionalProfile, User
from apps.catalog.models import Specialty, TradeCategory

from .models import VisitRequest


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
		category = TradeCategory.objects.create(name='Electricidad', keywords='enchufe, cable')
		self.specialty = Specialty.objects.create(category=category, name='Instalaciones eléctricas')
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

import logging
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db import IntegrityError
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.conf import settings
import mimetypes
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework.views import APIView

from .models import PasswordResetCode, ProfessionalProfile, User, VerificationCaseMessage
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.catalog.models import ProfessionalTrade, Specialty, TradeCategory
from apps.visits.models import AfterSalesClaim, ContentProgress, Notification, ProfessionalContent, Rating, SupportTicket, VisitRequest
from apps.visits.serializers import ClaimSerializer, ContentProgressSerializer, RatingSerializer, TicketSerializer, VisitRequestSerializer

from .serializers import (
    LoginSerializer,
    OverolTokenObtainPairSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    VerificationCaseMessageSerializer,
    VerificationDocumentsSerializer,
)

logger = logging.getLogger(__name__)
PASSWORD_RESET_CODE_LENGTH = 6
PASSWORD_RESET_CODE_LIFETIME = timedelta(minutes=10)
PASSWORD_RESET_CODE_MAX_ATTEMPTS = 5
PASSWORD_RESET_MIN_INTERVAL = timedelta(minutes=1)


class PasswordResetEmailUnavailable(APIException):
	status_code = status.HTTP_503_SERVICE_UNAVAILABLE
	default_detail = 'No fue posible enviar el correo de recuperación. Inténtalo más tarde.'
	default_code = 'password_reset_email_unavailable'


class OverolTokenObtainPairView(TokenObtainPairView):
	serializer_class = OverolTokenObtainPairSerializer


@staff_member_required
def local_dashboard(request):
	"""Panel temporal para ejecutar flujos de usuario en la base local."""
	actors = User.objects.filter(role__in=(User.Role.CLIENT, User.Role.PROFESSIONAL)).order_by('role', 'email')
	actor_id = request.session.get('local_actor_id')
	actor = User.objects.filter(pk=actor_id).first() if actor_id else None
	if request.method == 'POST':
		try:
			action = request.POST.get('action')
			if action == 'select_actor':
				request.session['local_actor_id'] = int(request.POST['actor_id'])
				return redirect('local-dashboard')
			if action == 'register':
				_register_local_user(request)
				messages.success(request, 'Usuario registrado correctamente.')
			elif action == 'create_visit':
				_require_actor(actor, User.Role.CLIENT)
				serializer = VisitRequestSerializer(data=request.POST, context={'request': _actor_request(request, actor)})
				serializer.is_valid(raise_exception=True)
				serializer.save()
				messages.success(request, 'Solicitud de visita creada.')
			elif action == 'visit_action':
				_require_actor(actor)
				_visit_action(request, actor)
				messages.success(request, 'Acción de visita ejecutada.')
			elif action == 'rate':
				_require_actor(actor)
				serializer = RatingSerializer(data=request.POST, context={'request': _actor_request(request, actor)})
				serializer.is_valid(raise_exception=True)
				serializer.save()
				messages.success(request, 'Calificación registrada.')
			elif action == 'create_ticket':
				_require_actor(actor)
				serializer = TicketSerializer(data=request.POST, context={'request': _actor_request(request, actor)})
				serializer.is_valid(raise_exception=True)
				serializer.save()
				messages.success(request, 'Ticket creado.')
			elif action == 'create_claim':
				_require_actor(actor, User.Role.CLIENT)
				serializer = ClaimSerializer(data=request.POST, context={'request': _actor_request(request, actor)})
				serializer.is_valid(raise_exception=True)
				serializer.save()
				messages.success(request, 'Reclamo creado.')
			elif action == 'resolve_ticket':
				_resolve_ticket(request)
				messages.success(request, 'Ticket resuelto.')
			elif action == 'resolve_claim':
				_resolve_claim(request)
				messages.success(request, 'Reclamo resuelto.')
			elif action == 'complete_content':
				_require_actor(actor, User.Role.PROFESSIONAL)
				ContentProgress.objects.get_or_create(
					professional=actor.professional_profile,
					content_id=request.POST['content_id'],
				)
				messages.success(request, 'Progreso registrado.')
		except (KeyError, ValueError, TypeError, DjangoValidationError, DRFValidationError, IntegrityError) as error:
			messages.error(request, f'Validación rechazada: {error}')
		return redirect('local-dashboard')

	visits = VisitRequest.objects.select_related('client', 'professional__user', 'specialty').order_by('-created_at')[:30]
	return render(request, 'local_dashboard/dashboard.html', {
		'actors': actors,
		'actor': actor,
		'categories': TradeCategory.objects.order_by('name'),
		'specialties': Specialty.objects.select_related('category').order_by('category__name', 'name'),
		'professionals': ProfessionalProfile.objects.select_related('user').filter(
			verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
		),
		'visits': visits,
		'ratings': Rating.objects.select_related('visit', 'author').order_by('-created_at')[:20],
		'tickets': SupportTicket.objects.select_related('user', 'visit').order_by('-created_at')[:20],
		'claims': AfterSalesClaim.objects.select_related('client', 'visit').order_by('-created_at')[:20],
		'contents': ProfessionalContent.objects.filter(is_visible=True).order_by('module', 'order'),
		'counts': _dashboard_counts(),
		'status_counts': [
			(status.label, VisitRequest.objects.filter(status=status.value).count())
			for status in VisitRequest.Status
		],
	})


def _dashboard_counts():
	return (
		('Usuarios', User.objects.count(), 'admin:authentication_user_changelist'),
		('Profesionales', ProfessionalProfile.objects.count(), 'admin:authentication_professionalprofile_changelist'),
		('Oficios', TradeCategory.objects.count(), 'admin:catalog_tradecategory_changelist'),
		('Especialidades', Specialty.objects.count(), 'admin:catalog_specialty_changelist'),
		('Solicitudes', VisitRequest.objects.count(), 'admin:visits_visitrequest_changelist'),
		('Calificaciones', Rating.objects.count(), 'admin:visits_rating_changelist'),
		('Reclamos', AfterSalesClaim.objects.count(), 'admin:visits_aftersalesclaim_changelist'),
		('Tickets', SupportTicket.objects.count(), 'admin:visits_supportticket_changelist'),
	)


def _actor_request(request, actor):
	request.user = actor
	return request


def _require_actor(actor, role=None):
	if actor is None or role and actor.role != role:
		raise ValueError('Selecciona un actor con el rol requerido.')


def _register_local_user(request):
	role = request.POST['role']
	profile = {}
	if role == User.Role.PROFESSIONAL:
		profile = {
			'coverage_communes': [request.POST.get('commune', 'Santiago')],
			'categories': [{'category': request.POST['category_id'], 'years_experience': request.POST.get('years_experience', 0)}],
			'specialties': [request.POST['specialty_id']] if request.POST.get('specialty_id') else [],
			'work_days': ['lunes', 'martes', 'miércoles', 'jueves', 'viernes'],
			'work_start': '09:00',
			'work_end': '18:00',
			'bio': request.POST.get('bio', ''),
		}
	data = request.POST.dict()
	data['privacy_policy_accepted'] = 'true'
	data['privacy_policy_version'] = 'local-demo-1'
	data['professional_profile'] = profile
	serializer = RegistrationSerializer(data=data)
	serializer.is_valid(raise_exception=True)
	serializer.save()


def _visit_action(request, actor):
	visit = VisitRequest.objects.select_related('professional__user', 'client').get(pk=request.POST['visit_id'])
	action = request.POST['visit_action']
	if action == 'accept' and actor == visit.professional.user:
		visit.accept()
	elif action == 'reject' and actor == visit.professional.user:
		visit.reject(request.POST.get('reason', 'Rechazo de demostración'))
	elif action == 'cancel' and actor == visit.client:
		visit.cancel()
	elif action == 'finish' and actor == visit.professional.user:
		visit.finish_by_professional()
	elif action == 'confirm' and actor == visit.client:
		visit.confirm_by_client()
	else:
		raise ValueError('El actor no puede ejecutar esta acción.')


def _resolve_ticket(request):
	ticket = SupportTicket.objects.get(pk=request.POST['ticket_id'])
	ticket.response = request.POST['response']
	ticket.status = SupportTicket.Status.RESOLVED
	ticket.save(update_fields=['response', 'status', 'updated_at'])


def _resolve_claim(request):
	claim = AfterSalesClaim.objects.get(pk=request.POST['claim_id'])
	claim.admin_resolution = request.POST['resolution']
	claim.status = AfterSalesClaim.Status.RESOLVED
	claim.resolved_at = timezone.now()
	claim.save(update_fields=['admin_resolution', 'status', 'resolved_at'])


class RegisterView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = RegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		return Response({'id': user.id, 'email': user.email, 'role': user.role}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.validated_data['user']
		login(request, user)
		return Response({'id': user.id, 'email': user.email, 'role': user.role})


class LogoutView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		refresh = request.data.get('refresh')
		if refresh:
			try:
				RefreshToken(refresh).blacklist()
			except TokenError as error:
				return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
		logout(request)
		return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser, JSONParser]

	def get(self, request):
		return Response(ProfileSerializer(request.user).data)

	def patch(self, request):
		serializer = ProfileSerializer(request.user, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		user_data = {key: value for key, value in serializer.validated_data.items() if key not in ('professional_profile',)}
		profile_data = serializer.validated_data.get('professional_profile', {})
		for key, value in user_data.items():
			setattr(request.user, key, value)
		request.user.save()
		if profile_data and hasattr(request.user, 'professional_profile'):
			profile = request.user.professional_profile
			for key, value in profile_data.items():
				setattr(profile, key, value)
			profile.save()
		return Response(serializer.data)


class ChangePasswordView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
		serializer.is_valid(raise_exception=True)
		request.user.set_password(serializer.validated_data['new_password'])
		request.user.save(update_fields=['password'])
		logout(request)
		return Response(status=status.HTTP_204_NO_CONTENT)


class OverolPasswordResetView(APIView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'password_reset'

	def post(self, request):
		serializer = PasswordResetRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		email = serializer.validated_data['email']
		now = timezone.now()
		with transaction.atomic():
			user = User.objects.select_for_update().filter(
				email__iexact=email,
				is_active=True,
			).first()
			if user and user.has_usable_password():
				last_request = user.password_reset_codes.order_by('-created_at').first()
				if not last_request or last_request.created_at <= now - PASSWORD_RESET_MIN_INTERVAL:
					PasswordResetCode.objects.filter(user=user).delete()
					code = f'{secrets.randbelow(10 ** PASSWORD_RESET_CODE_LENGTH):0{PASSWORD_RESET_CODE_LENGTH}d}'
					reset_code = PasswordResetCode.objects.create(
						user=user,
						code_hash=make_password(code),
						expires_at=now + PASSWORD_RESET_CODE_LIFETIME,
					)
					message = render_to_string(
						'registration/password_reset_code_email.txt',
						{'code': code},
					)
					try:
						send_mail(
							'Código de recuperación de Overol',
							message,
							settings.DEFAULT_FROM_EMAIL,
							[user.email],
							fail_silently=False,
						)
					except (OSError, SMTPException) as error:
						logger.exception('No se pudo enviar un código de recuperación.')
						raise PasswordResetEmailUnavailable() from error
		return Response(
			{'detail': 'Si el correo está registrado, recibirás un código para recuperar tu contraseña.'},
			status=status.HTTP_202_ACCEPTED,
		)


class PasswordResetConfirmView(APIView):
	permission_classes = [AllowAny]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'password_reset_confirm'

	def post(self, request):
		serializer = PasswordResetConfirmSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data
		now = timezone.now()
		with transaction.atomic():
			user = User.objects.select_for_update().filter(
				email__iexact=data['email'],
				is_active=True,
			).first()
			reset_code = None
			if user:
				reset_code = PasswordResetCode.objects.select_for_update().filter(
					user=user,
					consumed_at__isnull=True,
				).order_by('-created_at').first()
			if (
				not user
				or not reset_code
				or reset_code.expires_at <= now
				or reset_code.attempts >= PASSWORD_RESET_CODE_MAX_ATTEMPTS
			):
				return Response(
					{'detail': 'El código no es válido o ha expirado.'},
					status=status.HTTP_400_BAD_REQUEST,
				)

			if not check_password(data['code'], reset_code.code_hash):
				reset_code.attempts += 1
				if reset_code.attempts >= PASSWORD_RESET_CODE_MAX_ATTEMPTS:
					reset_code.consumed_at = now
				reset_code.save(update_fields=['attempts', 'consumed_at'])
				return Response(
					{'detail': 'El código no es válido o ha expirado.'},
					status=status.HTTP_400_BAD_REQUEST,
				)

			try:
				validate_password(data['new_password'], user)
			except DjangoValidationError as error:
				return Response({'new_password': error.messages}, status=status.HTTP_400_BAD_REQUEST)

			user.set_password(data['new_password'])
			user.save(update_fields=['password'])
			reset_code.consumed_at = now
			reset_code.save(update_fields=['consumed_at'])
			for outstanding_token in OutstandingToken.objects.filter(
				user=user,
				expires_at__gt=now,
			):
				BlacklistedToken.objects.get_or_create(token=outstanding_token)

		return Response(
			{'detail': 'La contraseña se restableció correctamente.'},
			status=status.HTTP_200_OK,
		)


class VerificationDocumentsView(APIView):
	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser]

	def get(self, request):
		profile = self._professional_profile(request)
		return Response({
			'professional_profile_id': profile.pk,
			'verification_status': profile.verification_status,
			'documents': {
				'front_uploaded': bool(profile.id_card_front),
				'back_uploaded': bool(profile.id_card_back),
			},
		})

	def post(self, request):
		profile = self._professional_profile(request)
		serializer = VerificationDocumentsSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		previous_names = {}
		updated_fields = []
		for field_name, upload in serializer.validated_data.items():
			old_file = getattr(profile, field_name)
			previous_names[field_name] = old_file.name if old_file else None
			setattr(profile, field_name, upload)
			updated_fields.append(field_name)

		profile.verification_status = ProfessionalProfile.VerificationStatus.PENDING
		profile.save(update_fields=updated_fields + ['verification_status'])

		for field_name, previous_name in previous_names.items():
			new_name = getattr(profile, field_name).name
			if previous_name and previous_name != new_name:
				getattr(profile, field_name).storage.delete(previous_name)

		return self.get(request)

	@staticmethod
	def _professional_profile(request):
		if request.user.role != User.Role.PROFESSIONAL:
			raise PermissionDenied('Solo los profesionales pueden cargar documentos de verificación.')
		try:
			return request.user.professional_profile
		except ProfessionalProfile.DoesNotExist:
			raise PermissionDenied('No se encontró el perfil profesional.')


class VerificationMessageListCreateView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		professional = self._professional(request)
		return Response(VerificationCaseMessageSerializer(professional.case_messages.all(), many=True).data)

	def post(self, request):
		professional = self._professional(request)
		serializer = VerificationCaseMessageSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		message = serializer.save(professional=professional)
		return Response(VerificationCaseMessageSerializer(message).data, status=status.HTTP_201_CREATED)

	@staticmethod
	def _professional(request):
		if request.user.role != request.user.Role.PROFESSIONAL:
			raise PermissionDenied('Solo los profesionales pueden gestionar su verificación.')
		return ProfessionalProfile.objects.get(user=request.user)


class VerificationDecisionView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk, decision):
		if request.user.role != request.user.Role.ADMIN:
			raise PermissionDenied('Solo un administrador puede resolver verificaciones.')
		profile = ProfessionalProfile.objects.get(pk=pk)
		reason = request.data.get('reason', '').strip()
		if decision not in ('approve', 'reject') or decision == 'reject' and not reason:
			return Response({'detail': 'Una decisión inválida o un motivo faltante.'}, status=status.HTTP_400_BAD_REQUEST)
		if decision == 'approve' and not (profile.id_card_front and profile.id_card_back):
			return Response(
				{'detail': 'El profesional debe cargar ambos lados de su cédula antes de ser aprobado.'},
				status=status.HTTP_400_BAD_REQUEST,
			)
		profile.verification_status = ProfessionalProfile.VerificationStatus.APPROVED if decision == 'approve' else ProfessionalProfile.VerificationStatus.REJECTED
		profile.save(update_fields=['verification_status'])
		from apps.visits.models import AdminAuditLog, Notification
		Notification.objects.create(
			recipient=profile.user,
			title='Resultado de verificación',
			message=reason or 'Tu identidad fue aprobada.',
		)
		AdminAuditLog.objects.create(
			administrator=request.user,
			action=f'verification_{decision}',
			reason=reason or 'Aprobación de identidad',
			target_type='ProfessionalProfile',
			target_id=profile.pk,
		)
		latest_message = profile.case_messages.first()
		if latest_message:
			latest_message.admin_response = reason or 'Verificación aprobada.'
			latest_message.resolved_at = timezone.now()
			latest_message.save(update_fields=['admin_response', 'resolved_at'])
		return Response({'status': profile.verification_status})


class AccountStatusView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		if request.user.role != request.user.Role.ADMIN:
			raise PermissionDenied('Solo un administrador puede cambiar estados de cuenta.')
		from apps.visits.models import AdminAuditLog, Notification
		target = User.objects.get(pk=pk)
		status_value = request.data.get('status')
		reason = request.data.get('reason', '').strip()
		allowed = {choice for choice, _ in User.AccountStatus.choices}
		if status_value not in allowed or not reason:
			return Response({'detail': 'El estado y el motivo son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)
		target.account_status = status_value
		target.is_active = status_value != User.AccountStatus.DEACTIVATED
		target.save(update_fields=['account_status', 'is_active'])
		AdminAuditLog.objects.create(
			administrator=request.user,
			action='account_status_change',
			reason=reason,
			target_type='User',
			target_id=target.pk,
		)
		Notification.objects.create(recipient=target, title='Estado de cuenta actualizado', message=reason)
		return Response({'id': target.pk, 'account_status': target.account_status})


class VerificationDocumentView(APIView):
	permission_classes = [IsAuthenticated, IsAdminUser]

	def get(self, request, pk):
		if request.user.role != User.Role.ADMIN:
			raise PermissionDenied('Solo un administrador puede acceder a documentos de verificación.')
		profile = ProfessionalProfile.objects.get(pk=pk)
		side = request.query_params.get('side', 'front')
		field = profile.id_card_back if side == 'back' else profile.id_card_front
		if side not in ('front', 'back'):
			return Response({'detail': 'side debe ser front o back.'}, status=status.HTTP_400_BAD_REQUEST)
		if not field:
			return Response({'detail': 'El documento solicitado no existe.'}, status=status.HTTP_404_NOT_FOUND)
		response = FileResponse(
			field.open('rb'),
			as_attachment=True,
			filename=field.name.rsplit('/', 1)[-1],
			content_type=mimetypes.guess_type(field.name)[0] or 'application/octet-stream',
		)
		response['X-Content-Type-Options'] = 'nosniff'
		return response

# Create your views here.

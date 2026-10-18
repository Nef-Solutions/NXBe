from django.contrib.auth import login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProfessionalProfile, User, VerificationCaseMessage
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginSerializer, OverolTokenObtainPairSerializer, PasswordChangeSerializer, ProfileSerializer, RegistrationSerializer, VerificationCaseMessageSerializer


class OverolTokenObtainPairView(TokenObtainPairView):
	serializer_class = OverolTokenObtainPairSerializer


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
		logout(request)
		return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		return Response(ProfileSerializer(request.user).data)

	def patch(self, request):
		serializer = ProfileSerializer(request.user, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
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

	def post(self, request):
		form = PasswordResetForm(request.data)
		if form.is_valid():
			form.save(request=request, use_https=request.is_secure())
		return Response(
			{'detail': 'Si el correo está registrado, recibirás instrucciones para recuperar tu contraseña.'},
			status=status.HTTP_202_ACCEPTED,
		)


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

# Create your views here.

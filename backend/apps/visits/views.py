from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListCreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import ProfessionalProfile

from .models import AdminAuditLog, AfterSalesClaim, ContentProgress, Notification, ProfessionalContent, SupportTicket, VisitRequest
from .serializers import ClaimSerializer, ContentProgressSerializer, ContentSerializer, NotificationSerializer, RatingSerializer, RejectSerializer, TicketSerializer, VisitRequestSerializer


def notify(recipient, title, message, visit=None):
	return Notification.objects.create(recipient=recipient, title=title, message=message, related_visit=visit)


class VisitListCreateView(ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = VisitRequestSerializer

	def get_queryset(self):
		user = self.request.user
		if user.role == user.Role.PROFESSIONAL:
			return VisitRequest.objects.filter(professional__user=user).select_related('client', 'professional', 'specialty')
		return VisitRequest.objects.filter(client=user).select_related('professional', 'specialty')


class VisitActionView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk, action):
		visit = get_object_or_404(VisitRequest.objects.select_related('client', 'professional__user'), pk=pk)
		try:
			if action == 'accept':
				self._professional_only(request, visit)
				visit.accept()
				notify(visit.client, 'Solicitud aceptada', 'El profesional aceptó tu solicitud.', visit)
			elif action == 'reject':
				self._professional_only(request, visit)
				data = RejectSerializer(data=request.data)
				data.is_valid(raise_exception=True)
				visit.reject(data.validated_data['reason'])
				notify(visit.client, 'Solicitud rechazada', data.validated_data['reason'], visit)
			elif action == 'cancel':
				self._client_only(request, visit)
				visit.cancel()
				notify(visit.professional.user, 'Solicitud cancelada', 'El cliente canceló la solicitud.', visit)
			elif action == 'finish':
				self._professional_only(request, visit)
				visit.finish_by_professional()
				notify(visit.client, 'Confirma la finalización', 'El profesional informó que terminó el servicio.', visit)
			elif action == 'confirm':
				self._client_only(request, visit)
				visit.confirm_by_client()
				notify(visit.professional.user, 'Servicio confirmado', 'El cliente confirmó la finalización.', visit)
			else:
				return Response({'detail': 'Acción no soportada.'}, status=status.HTTP_400_BAD_REQUEST)
		except PermissionDenied:
			raise
		except ValueError as error:
			if 'permisos' in str(error):
				raise PermissionDenied(str(error))
			return Response({'detail': str(error)}, status=status.HTTP_409_CONFLICT)
		return Response(VisitRequestSerializer(visit).data)

	@staticmethod
	def _professional_only(request, visit):
		if request.user != visit.professional.user:
			raise ValueError('No tienes permisos para esta solicitud.')

	@staticmethod
	def _client_only(request, visit):
		if request.user != visit.client:
			raise ValueError('No tienes permisos para esta solicitud.')


class RatingCreateView(CreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = RatingSerializer


class ClaimListCreateView(ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = ClaimSerializer

	def get_queryset(self):
		user = self.request.user
		return AfterSalesClaim.objects.filter(visit__client=user) | AfterSalesClaim.objects.filter(visit__professional__user=user)


class ClaimActionView(APIView):

	permission_classes = [IsAuthenticated]

	def post(self, request, pk, action):
		claim = get_object_or_404(AfterSalesClaim.objects.select_related('visit__professional__user'), pk=pk)
		if action == 'respond':
			if request.user != claim.visit.professional.user or claim.status != AfterSalesClaim.Status.OPEN:
				raise PermissionDenied('No puedes responder este reclamo.')
			response = request.data.get('response', '').strip()
			if not response:
				return Response({'detail': 'La respuesta es obligatoria.'}, status=status.HTTP_400_BAD_REQUEST)
			claim.professional_response = response
			claim.status = AfterSalesClaim.Status.PROFESSIONAL_RESPONDED
			claim.save(update_fields=['professional_response', 'status'])
			notify(claim.client, 'Respuesta de posventa', response)
		elif action == 'escalate':
			if request.user not in (claim.client, claim.visit.professional.user):
				raise PermissionDenied('No puedes escalar este reclamo.')
			claim.status = AfterSalesClaim.Status.ESCALATED
			claim.save(update_fields=['status'])
		elif action == 'resolve':
			if request.user.role != request.user.Role.ADMIN:
				raise PermissionDenied('Solo un administrador puede resolver reclamos.')
			resolution = request.data.get('resolution', '').strip()
			if not resolution:
				return Response({'detail': 'La resolución es obligatoria.'}, status=status.HTTP_400_BAD_REQUEST)
			claim.admin_resolution = resolution
			claim.status = AfterSalesClaim.Status.RESOLVED
			claim.resolved_at = timezone.now()
			claim.save(update_fields=['admin_resolution', 'status', 'resolved_at'])
			AdminAuditLog.objects.create(administrator=request.user, action='resolve_claim', reason=resolution, target_type='AfterSalesClaim', target_id=claim.pk)
		else:
			return Response({'detail': 'Acción no soportada.'}, status=status.HTTP_400_BAD_REQUEST)
		return Response(ClaimSerializer(claim).data)


class TicketListCreateView(ListCreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = TicketSerializer

	def get_queryset(self):
		return SupportTicket.objects.filter(user=self.request.user)


class TicketResolveView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		if request.user.role != request.user.Role.ADMIN:
			raise PermissionDenied('Solo un administrador puede resolver tickets.')
		ticket = get_object_or_404(SupportTicket, pk=pk)
		response = request.data.get('response', '').strip()
		if not response:
			return Response({'detail': 'La respuesta es obligatoria.'}, status=status.HTTP_400_BAD_REQUEST)
		ticket.response = response
		ticket.status = SupportTicket.Status.RESOLVED
		ticket.save(update_fields=['response', 'status', 'updated_at'])
		AdminAuditLog.objects.create(administrator=request.user, action='resolve_ticket', reason=response, target_type='SupportTicket', target_id=ticket.pk)
		notify(ticket.user, 'Ticket resuelto', response)
		return Response(TicketSerializer(ticket).data)


class NotificationListView(ListAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = NotificationSerializer

	def get_queryset(self):
		return Notification.objects.filter(recipient=self.request.user)


class NotificationReadView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
		notification.is_read = True
		notification.save(update_fields=['is_read'])
		return Response(NotificationSerializer(notification).data)


class ProfessionalContentListView(ListAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = ContentSerializer
	queryset = ProfessionalContent.objects.filter(is_visible=True).order_by('module', 'order')

	def get(self, request, *args, **kwargs):
		if request.user.role != request.user.Role.PROFESSIONAL:
			return Response({'detail': 'Solo los profesionales pueden acceder.'}, status=status.HTTP_403_FORBIDDEN)
		return super().get(request, *args, **kwargs)


class ContentProgressCreateView(CreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = ContentProgressSerializer

	def perform_create(self, serializer):
		from rest_framework.exceptions import PermissionDenied
		if self.request.user.role != self.request.user.Role.PROFESSIONAL:
			raise PermissionDenied('Solo los profesionales pueden registrar progreso.')
		professional = get_object_or_404(ProfessionalProfile, user=self.request.user)
		serializer.save(professional=professional)

# Create your views here.

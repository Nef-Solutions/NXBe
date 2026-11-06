from datetime import datetime, timedelta
import re

from rest_framework import serializers
from django.db.models import Avg
from django.utils import timezone

from apps.authentication.models import ProfessionalProfile

from .models import AfterSalesClaim, ContentProgress, Notification, ProfessionalContent, Rating, SupportTicket, VisitRequest
from .services import expire_pending_requests


class VisitRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    professional_name = serializers.CharField(source='professional.user.get_full_name', read_only=True)
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)
    category_name = serializers.CharField(source='specialty.category.name', read_only=True)
    phone = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    contact_commune = serializers.SerializerMethodField()

    class Meta:
        model = VisitRequest
        fields = ('id', 'client', 'client_name', 'professional', 'professional_name', 'specialty', 'specialty_name',
                  'category_name', 'problem_description', 'tentative_schedule', 'visit_date', 'visit_time',
                  'commune', 'home_zone', 'visit_address', 'status', 'rejection_reason', 'cancelled_by',
                  'cancel_reason', 'client_confirmed_at', 'professional_confirmed_at', 'completed_at', 'expires_at',
                  'phone', 'address', 'contact_commune', 'created_at')
        read_only_fields = ('id', 'client', 'status', 'rejection_reason', 'cancelled_by', 'cancel_reason',
                            'client_confirmed_at', 'professional_confirmed_at', 'completed_at', 'expires_at', 'created_at')

    def _contact_allowed(self, obj):
        request_user = self.context['request'].user
        return (
            request_user in (obj.client, obj.professional.user)
            and obj.status in (
                VisitRequest.Status.ACCEPTED,
                VisitRequest.Status.PROFESSIONAL_FINISHED,
                VisitRequest.Status.COMPLETED,
            )
        )

    def get_phone(self, obj):
        if not self._contact_allowed(obj):
            return None
        user = obj.professional.user if self.context['request'].user == obj.client else obj.client
        return user.phone

    def get_address(self, obj):
        if not self._contact_allowed(obj):
            return None
        user = obj.professional.user if self.context['request'].user == obj.client else obj.client
        return user.address if self.context['request'].user in (obj.client, obj.professional.user) else None

    def get_contact_commune(self, obj):
        if not self._contact_allowed(obj):
            return None
        user = obj.professional.user if self.context['request'].user == obj.client else obj.client
        return user.commune

    @staticmethod
    def _day_matches(visit_date, work_days):
        english_days = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
        spanish_days = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
        day_index = visit_date.weekday()
        configured = {str(day).strip().lower() for day in (work_days or [])}
        return (
            english_days[day_index] in configured
            or spanish_days[day_index] in configured
            or str(day_index) in configured
            or str(day_index + 1) in configured
        )

    @staticmethod
    def _time_bounds(value):
        if not value:
            return None, None
        parts = re.split(r'\s*(?:-|–|—|a)\s*', str(value), maxsplit=1, flags=re.IGNORECASE)
        try:
            start = datetime.strptime(parts[0].strip(), '%H:%M').time()
            end = datetime.strptime(parts[-1].strip(), '%H:%M').time()
        except ValueError:
            raise serializers.ValidationError({'visit_time': 'La hora debe usar HH:MM o HH:MM - HH:MM.'})
        return start, end

    def validate(self, attrs):
        request = self.context['request']
        expire_pending_requests()
        professional = attrs['professional']
        specialty = attrs['specialty']
        if request.user.role != request.user.Role.CLIENT:
            raise serializers.ValidationError('Solo un cliente puede solicitar una visita.')
        if professional.verification_status != ProfessionalProfile.VerificationStatus.APPROVED:
            raise serializers.ValidationError('El profesional no está verificado.')
        if not specialty.professionals.filter(pk=professional.pk).exists():
            raise serializers.ValidationError('La especialidad no pertenece al profesional seleccionado.')
        if attrs.get('visit_date') and attrs['visit_date'] < timezone.localdate():
            raise serializers.ValidationError({'visit_date': 'La fecha no puede estar en el pasado.'})
        if not attrs.get('visit_date'):
            raise serializers.ValidationError({'visit_date': 'La fecha de visita es obligatoria.'})
        if not attrs.get('visit_time'):
            raise serializers.ValidationError({'visit_time': 'La hora de visita es obligatoria.'})
        if not self._day_matches(attrs['visit_date'], professional.work_days):
            raise serializers.ValidationError({'visit_date': 'La solicitud está fuera de los días de atención del profesional.'})
        if professional.work_start is None or professional.work_end is None:
            raise serializers.ValidationError({'visit_time': 'El profesional no tiene un horario de atención configurado.'})
        start, end = self._time_bounds(attrs['visit_time'])
        if end <= start or start < professional.work_start or end > professional.work_end:
            raise serializers.ValidationError({'visit_time': 'La solicitud está fuera del horario de atención del profesional.'})
        if VisitRequest.objects.filter(client=request.user, professional=professional, status=VisitRequest.Status.PENDING).exists():
            raise serializers.ValidationError('Ya tienes una solicitud pendiente para este profesional.')
        if not professional.is_available:
            raise serializers.ValidationError('El profesional no está disponible.')
        if attrs.get('commune') and professional.coverage_communes and attrs['commune'] not in professional.coverage_communes:
            raise serializers.ValidationError({'commune': 'La comuna está fuera de la cobertura del profesional.'})
        return attrs

    def create(self, validated_data):
        request = VisitRequest.objects.create(client=self.context['request'].user, **validated_data)
        request.expires_at = request.created_at + timedelta(days=30)
        request.save(update_fields=['expires_at'])
        return request


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ('id', 'visit', 'quality', 'punctuality', 'treatment', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_visit(self, visit):
        if visit.status != VisitRequest.Status.COMPLETED:
            raise serializers.ValidationError('El servicio debe estar completado.')
        if not visit.completed_at or timezone.now() > visit.completed_at + timedelta(days=30):
            raise serializers.ValidationError('El plazo para calificar este servicio expiró.')
        return visit

    def validate(self, attrs):
        visit = attrs.get('visit')
        author = self.context['request'].user
        if visit and author not in (visit.client, visit.professional.user):
            raise serializers.ValidationError({'visit': 'No puedes calificar este servicio.'})
        if visit and Rating.objects.filter(visit=visit, author=author).exists():
            raise serializers.ValidationError({'visit': 'Este servicio ya fue calificado por este usuario.'})
        return attrs

    def create(self, validated_data):
        visit = validated_data['visit']
        author = self.context['request'].user
        target = visit.professional.user if author == visit.client else visit.client
        rating = Rating.objects.create(author=author, target=target, trade=None, **validated_data)
        if target == visit.professional.user:
            scores = Rating.objects.filter(target=target).aggregate(
                quality=Avg('quality'),
                punctuality=Avg('punctuality'),
                treatment=Avg('treatment'),
            )
            average = sum(value or 0 for value in scores.values()) / 3
            visit.professional.rating_avg = average
            visit.professional.save(update_fields=['rating_avg'])
        return rating


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = AfterSalesClaim
        fields = ('id', 'visit', 'description', 'professional_response', 'admin_resolution', 'status', 'created_at', 'resolved_at')
        read_only_fields = ('id', 'professional_response', 'admin_resolution', 'status', 'created_at', 'resolved_at')

    def validate_visit(self, visit):
        if visit.status != VisitRequest.Status.COMPLETED:
            raise serializers.ValidationError('Solo se puede reclamar un servicio completado.')
        if visit.client_id != self.context['request'].user.id:
            raise serializers.ValidationError('Solo el cliente del servicio puede reclamarlo.')
        return visit

    def create(self, validated_data):
        return AfterSalesClaim.objects.create(client=self.context['request'].user, **validated_data)


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ('id', 'visit', 'subject', 'description', 'response', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'response', 'status', 'created_at', 'updated_at')
        extra_kwargs = {
            'description': {'max_length': 500},
            'visit': {'required': True},
        }

    def create(self, validated_data):
        visit = validated_data.get('visit')
        if visit.client_id != self.context['request'].user.id and visit.professional.user_id != self.context['request'].user.id:
            raise serializers.ValidationError({'visit': 'La solicitud no pertenece al usuario.'})
        return SupportTicket.objects.create(user=self.context['request'].user, **validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'message', 'related_visit', 'is_read', 'created_at')
        read_only_fields = fields


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalContent
        fields = ('id', 'title', 'description', 'module', 'url', 'is_external', 'order')
        read_only_fields = fields


class ContentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentProgress
        fields = ('id', 'content', 'completed_at')
        read_only_fields = ('id', 'completed_at')
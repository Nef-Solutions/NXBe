from rest_framework import serializers
from django.db.models import Avg

from apps.authentication.models import ProfessionalProfile

from .models import AfterSalesClaim, ContentProgress, Notification, ProfessionalContent, Rating, SupportTicket, VisitRequest


class VisitRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitRequest
        fields = ('id', 'professional', 'specialty', 'problem_description', 'tentative_schedule', 'visit_address', 'status', 'rejection_reason', 'created_at')
        read_only_fields = ('id', 'status', 'rejection_reason', 'created_at')

    def validate(self, attrs):
        request = self.context['request']
        professional = attrs['professional']
        specialty = attrs['specialty']
        if request.user.role != request.user.Role.CLIENT:
            raise serializers.ValidationError('Solo un cliente puede solicitar una visita.')
        if professional.verification_status != ProfessionalProfile.VerificationStatus.APPROVED:
            raise serializers.ValidationError('El profesional no está verificado.')
        if not specialty.professionals.filter(pk=professional.pk).exists():
            raise serializers.ValidationError('La especialidad no pertenece al profesional seleccionado.')
        return attrs

    def create(self, validated_data):
        return VisitRequest.objects.create(client=self.context['request'].user, **validated_data)


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField()


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ('id', 'visit', 'quality', 'punctuality', 'treatment', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_visit(self, visit):
        if visit.status != VisitRequest.Status.COMPLETED:
            raise serializers.ValidationError('El servicio debe estar completado.')
        return visit

    def create(self, validated_data):
        visit = validated_data['visit']
        author = self.context['request'].user
        if author not in (visit.client, visit.professional.user):
            raise serializers.ValidationError('No puedes calificar este servicio.')
        target = visit.professional.user if author == visit.client else visit.client
        rating = Rating.objects.create(author=author, target=target, **validated_data)
        if target == visit.professional.user:
            scores = Rating.objects.filter(target=target).aggregate(
                quality=Avg('quality'),
                punctuality=Avg('punctuality'),
                treatment=Avg('treatment'),
            )
            average = sum(scores.values()) / 3
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

    def create(self, validated_data):
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
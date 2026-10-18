from rest_framework import serializers

from apps.authentication.models import ProfessionalProfile
from .models import ProfessionalTrade


class ProfessionalResultSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    specialties = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalProfile
        fields = ('id', 'name', 'specialties', 'categories', 'visit_fee', 'rating_avg', 'verification_status', 'trades')

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_specialties(self, obj):
        return list(obj.specialties.values_list('name', flat=True))

    def get_categories(self, obj):
        return list(obj.specialties.values_list('category__name', flat=True).distinct())

    def get_trades(self, obj):
        return list(obj.trades.filter(is_active=True).values('category__name', 'years_experience', 'description', 'certification_verified'))


class ProfessionalDetailSerializer(ProfessionalResultSerializer):
    opinions = serializers.SerializerMethodField()

    class Meta(ProfessionalResultSerializer.Meta):
        fields = ProfessionalResultSerializer.Meta.fields + ('opinions',)

    def get_opinions(self, obj):
        from apps.visits.models import Rating
        return list(Rating.objects.filter(target=obj.user).values('quality', 'punctuality', 'treatment', 'comment', 'created_at').order_by('-created_at'))
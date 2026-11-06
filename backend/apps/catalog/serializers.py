from rest_framework import serializers

from apps.authentication.models import ProfessionalProfile
from .models import HomeZone, ProfessionalTrade, Specialty, TradeCategory


class ProfessionalResultSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    specialties = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()
    commune = serializers.SerializerMethodField()
    bio = serializers.CharField(read_only=True)
    coverage = serializers.SerializerMethodField()
    work_days = serializers.ListField(read_only=True)
    work_start = serializers.TimeField(read_only=True)
    work_end = serializers.TimeField(read_only=True)
    trades = serializers.SerializerMethodField()
    rut = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalProfile
        fields = ('id', 'name', 'first_name', 'last_name', 'specialties', 'categories', 'visit_fee', 'rating_avg',
                  'verification_status', 'trades', 'profile_photo', 'commune', 'bio', 'coverage', 'work_days',
                  'work_start', 'work_end', 'rut', 'address')

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_specialties(self, obj):
        return list(obj.specialties.values_list('name', flat=True))

    def get_categories(self, obj):
        return list(obj.specialties.values_list('category__name', flat=True).distinct())

    def get_trades(self, obj):
        return [
            {
                'id': trade.id,
                'category_id': trade.category_id,
                'category': trade.category.name,
                'years_experience': trade.years_experience,
                'description': trade.description,
                'specialties': list(obj.specialties.filter(category=trade.category).values('id', 'name')),
            }
            for trade in obj.trades.filter(is_active=True).select_related('category')
        ]

    def get_profile_photo(self, obj):
        return obj.user.profile_photo.url if obj.user.profile_photo else None

    def get_coverage(self, obj):
        return obj.coverage_communes

    def get_commune(self, obj):
        return obj.user.commune if self._is_admin() else None

    def _is_admin(self):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and request.user.role == request.user.Role.ADMIN)

    def get_rut(self, obj):
        return obj.rut if self._is_admin() else None

    def get_address(self, obj):
        return obj.user.address if self._is_admin() else None


class ProfessionalDetailSerializer(ProfessionalResultSerializer):
    opinions = serializers.SerializerMethodField()

    class Meta(ProfessionalResultSerializer.Meta):
        fields = ProfessionalResultSerializer.Meta.fields + ('opinions',)

    def get_opinions(self, obj):
        from apps.visits.models import Rating
        return [{
            'quality': rating.quality,
            'punctuality': rating.punctuality,
            'treatment': rating.treatment,
            'comment': rating.comment,
            'created_at': rating.created_at,
            'author_name': f"{rating.author.first_name} {rating.author.last_name[:1]}.",
        } for rating in Rating.objects.filter(target=obj.user).select_related(
            'author'
        ).order_by('-created_at')]


class CategorySerializer(serializers.ModelSerializer):
    home_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    class Meta:
        model = TradeCategory
        fields = ('id', 'name', 'keywords', 'home_zones')


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ('id', 'name', 'category_id')


class HomeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeZone
        fields = ('id', 'name')


class TradeSerializer(serializers.ModelSerializer):
    specialties = serializers.PrimaryKeyRelatedField(many=True, queryset=Specialty.objects.all(), required=False, write_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source='category', queryset=TradeCategory.objects.all())

    class Meta:
        model = ProfessionalTrade
        fields = ('id', 'category_id', 'years_experience', 'description', 'certification',
                  'certification_verified', 'is_active', 'specialties')
        read_only_fields = ('id', 'certification_verified', 'is_active')

    def create(self, validated_data):
        specialties = validated_data.pop('specialties', [])
        trade = ProfessionalTrade.objects.create(professional=self.context['professional'], **validated_data)
        self.context['professional'].specialties.add(*specialties)
        return trade

    def update(self, instance, validated_data):
        specialties = validated_data.pop('specialties', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if specialties is not None:
            instance.professional.specialties.add(*specialties)
        return instance
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, ProfessionalProfile, VerificationCaseMessage


class AccountLocked(APIException):
    status_code = 429
    default_detail = 'La cuenta está temporalmente bloqueada.'
    default_code = 'account_locked'
from .validators import validate_rut_chileno


class RegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    privacy_policy_accepted = serializers.BooleanField(write_only=True)
    privacy_policy_version = serializers.CharField(write_only=True, max_length=30)
    professional_profile = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            'email', 'username', 'first_name', 'last_name', 'phone', 'rut',
            'address', 'commune', 'role', 'password', 'privacy_policy_accepted',
            'privacy_policy_version', 'professional_profile',
        )

    def validate_rut(self, value):
        return validate_rut_chileno(value)

    def validate_first_name(self, value):
        try:
            return User(first_name=value).clean() or value
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

    def validate_last_name(self, value):
        try:
            return User(last_name=value).clean() or value
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

    def validate(self, attrs):
        if not attrs.pop('privacy_policy_accepted', False):
            raise serializers.ValidationError({'privacy_policy_accepted': 'Debe aceptar la política de privacidad y los términos de uso.'})
        if not attrs.get('privacy_policy_version'):
            raise serializers.ValidationError({'privacy_policy_version': 'Debe indicar la versión aceptada.'})
        if attrs.get('role') not in (User.Role.CLIENT, User.Role.PROFESSIONAL):
            raise serializers.ValidationError({'role': 'El rol de registro no es válido.'})
        professional_data = attrs.get('professional_profile') or {}
        if attrs.get('role') == User.Role.PROFESSIONAL and not attrs.get('professional_profile'):
            raise serializers.ValidationError({'professional_profile': 'Los datos profesionales son obligatorios.'})
        if attrs.get('role') == User.Role.PROFESSIONAL:
            coverage = professional_data.get('coverage_communes')
            categories = professional_data.get('categories', professional_data.get('trades', []))
            if not isinstance(coverage, list) or not coverage:
                raise serializers.ValidationError({'professional_profile': {'coverage_communes': 'Debe indicar al menos una comuna de cobertura.'}})
            if not isinstance(categories, list) or not categories:
                raise serializers.ValidationError({'professional_profile': {'categories': 'Debe indicar al menos un oficio.'}})
        if not attrs.get('rut'):
            raise serializers.ValidationError({'rut': 'El RUT es obligatorio.'})
        password = attrs.get('password')
        try:
            validate_password(password)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': error.messages})
        if attrs.get('role') == User.Role.PROFESSIONAL and not attrs.get('address'):
            raise serializers.ValidationError({'address': 'La dirección es obligatoria para profesionales.'})
        return attrs

    def create(self, validated_data):
        professional_data = validated_data.pop('professional_profile', None)
        privacy_version = validated_data.pop('privacy_policy_version')
        password = validated_data.pop('password')
        validated_data['username'] = validated_data.get('username') or validated_data['email']
        user = User(**validated_data)
        user.accept_privacy_policy(privacy_version)
        user.set_password(password)
        user.save()
        if user.role == User.Role.PROFESSIONAL:
            profile_fields = {
                'id_card_front', 'id_card_back', 'visit_fee', 'bio', 'headline',
                'contact_preference', 'certifications', 'work_days', 'work_start',
                'work_end', 'is_available', 'coverage_communes',
                'service_latitude', 'service_longitude',
            }
            profile_data = {key: value for key, value in professional_data.items() if key in profile_fields}
            categories = professional_data.get('categories', professional_data.get('trades', []))
            specialties = professional_data.get('specialties', [])
            profile = ProfessionalProfile.objects.create(user=user, rut=user.rut, **profile_data)
            from apps.catalog.models import ProfessionalTrade, Specialty, TradeCategory
            for category_data in categories:
                category_id = category_data.get('category') if isinstance(category_data, dict) else category_data
                category = None
                try:
                    category = TradeCategory.objects.filter(pk=int(category_id)).first()
                except (TypeError, ValueError):
                    pass
                if category is None and isinstance(category_id, str):
                    category = TradeCategory.objects.filter(name__iexact=category_id.strip()).first()
                if category:
                    trade = ProfessionalTrade.objects.create(
                        professional=profile, category=category,
                        years_experience=category_data.get('years_experience', 0) if isinstance(category_data, dict) else 0,
                        description=category_data.get('description', '') if isinstance(category_data, dict) else '',
                    )
                    selected = category_data.get('specialties', []) if isinstance(category_data, dict) else specialties
                    profile.specialties.add(*Specialty.objects.filter(pk__in=selected, category=category))
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user_model = get_user_model()
        user_record = user_model.objects.filter(email__iexact=attrs['email']).first()
        if user_record and user_record.locked_until and user_record.locked_until > timezone.now():
            retry_after = max(1, int((user_record.locked_until - timezone.now()).total_seconds()))
            raise AccountLocked({'detail': 'La cuenta está temporalmente bloqueada.', 'retry_after': retry_after})
        if user_record and user_record.account_status != user_model.AccountStatus.ACTIVE:
            raise serializers.ValidationError('Credenciales inválidas.')
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user or not user.is_active:
            if user_record:
                user_record.failed_login_attempts += 1
                if user_record.failed_login_attempts >= 3:
                    user_record.locked_until = timezone.now() + timedelta(minutes=5)
                user_record.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise serializers.ValidationError('Credenciales inválidas.')
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=['failed_login_attempts', 'locked_until'])
        attrs['user'] = user
        return attrs


class OverolTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        user_model = get_user_model()
        email = attrs.get(user_model.USERNAME_FIELD)
        user_record = user_model.objects.filter(email__iexact=email).first()
        if user_record and user_record.locked_until and user_record.locked_until > timezone.now():
            retry_after = max(1, int((user_record.locked_until - timezone.now()).total_seconds()))
            raise AccountLocked({'detail': 'La cuenta está temporalmente bloqueada.', 'retry_after': retry_after})
        if user_record and user_record.account_status != user_model.AccountStatus.ACTIVE:
            raise AuthenticationFailed('Credenciales inválidas.')
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if user_record:
                user_record.failed_login_attempts += 1
                if user_record.failed_login_attempts >= 3:
                    user_record.locked_until = timezone.now() + timedelta(minutes=5)
                user_record.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise
        self.user.failed_login_attempts = 0
        self.user.locked_until = None
        self.user.save(update_fields=['failed_login_attempts', 'locked_until'])
        return data


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    professional_profile_id = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()
    client_rating_avg = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'phone', 'rut', 'address', 'commune', 'role',
                  'profile_photo', 'bio', 'headline', 'visit_fee', 'contact_preference', 'certifications',
                  'professional_profile_id', 'verification_status', 'client_rating_avg')
        read_only_fields = ('email', 'username', 'first_name', 'last_name', 'rut', 'role')

    bio = serializers.CharField(source='professional_profile.bio', max_length=500, required=False)
    headline = serializers.CharField(source='professional_profile.headline', required=False)
    visit_fee = serializers.DecimalField(source='professional_profile.visit_fee', max_digits=10, decimal_places=0, required=False)
    contact_preference = serializers.CharField(source='professional_profile.contact_preference', required=False)
    certifications = serializers.FileField(source='professional_profile.certifications', required=False)

    def get_professional_profile_id(self, obj):
        return getattr(getattr(obj, 'professional_profile', None), 'id', None)

    def get_verification_status(self, obj):
        return getattr(getattr(obj, 'professional_profile', None), 'verification_status', None)

    def get_client_rating_avg(self, obj):
        from django.db.models import Avg
        value = obj.ratings_received.filter(target=obj).aggregate(value=Avg('quality'))['value']
        return value

    def validate_profile_photo(self, value):
        if value and (value.size > 5 * 1024 * 1024 or value.content_type not in ('image/jpeg', 'image/png')):
            raise serializers.ValidationError('La foto debe ser JPG o PNG y no superar 5 MB.')
        return value

    def validate_certifications(self, value):
        if value and (value.size > 5 * 1024 * 1024 or value.content_type not in ('application/pdf', 'image/jpeg', 'image/png')):
            raise serializers.ValidationError('La certificación debe ser PDF, JPG o PNG y no superar 5 MB.')
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'La contraseña actual no es correcta.'})
        try:
            validate_password(attrs['new_password'], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': error.messages})
        return attrs


class VerificationCaseMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCaseMessage
        fields = ('id', 'professional', 'message', 'admin_response', 'resolved_at', 'created_at')
        read_only_fields = ('id', 'professional', 'admin_response', 'resolved_at', 'created_at')
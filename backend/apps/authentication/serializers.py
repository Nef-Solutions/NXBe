from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, ProfessionalProfile, VerificationCaseMessage
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

    def validate(self, attrs):
        if not attrs.pop('privacy_policy_accepted', False):
            raise serializers.ValidationError({'privacy_policy_accepted': 'Debe aceptar la política de privacidad y los términos de uso.'})
        if not attrs.get('privacy_policy_version'):
            raise serializers.ValidationError({'privacy_policy_version': 'Debe indicar la versión aceptada.'})
        if attrs.get('role') == User.Role.PROFESSIONAL and not attrs.get('professional_profile'):
            raise serializers.ValidationError({'professional_profile': 'Los datos profesionales son obligatorios.'})
        if not attrs.get('rut'):
            raise serializers.ValidationError({'rut': 'El RUT es obligatorio.'})
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
            profile_fields = {'id_card_front', 'id_card_back', 'visit_fee'}
            profile_data = {key: value for key, value in professional_data.items() if key in profile_fields}
            ProfessionalProfile.objects.create(user=user, rut=user.rut, **profile_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user_model = get_user_model()
        user_record = user_model.objects.filter(email__iexact=attrs['email']).first()
        if user_record and user_record.locked_until and user_record.locked_until > timezone.now():
            raise serializers.ValidationError('Credenciales inválidas.')
        if user_record and user_record.account_status != user_model.AccountStatus.ACTIVE:
            raise serializers.ValidationError('Credenciales inválidas.')
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user or not user.is_active:
            if user_record:
                user_record.failed_login_attempts += 1
                if user_record.failed_login_attempts >= 3:
                    user_record.locked_until = timezone.now() + timedelta(hours=6)
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
            raise AuthenticationFailed('Credenciales inválidas.')
        if user_record and user_record.account_status != user_model.AccountStatus.ACTIVE:
            raise AuthenticationFailed('Credenciales inválidas.')
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if user_record:
                user_record.failed_login_attempts += 1
                if user_record.failed_login_attempts >= 3:
                    user_record.locked_until = timezone.now() + timedelta(hours=6)
                user_record.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise
        self.user.failed_login_attempts = 0
        self.user.locked_until = None
        self.user.save(update_fields=['failed_login_attempts', 'locked_until'])
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'phone', 'rut', 'address', 'commune', 'role')
        read_only_fields = ('email', 'username', 'first_name', 'last_name', 'rut', 'role')


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
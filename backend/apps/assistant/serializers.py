from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1500, trim_whitespace=True)

    def validate_message(self, value):
        if not value:
            raise serializers.ValidationError('Escribe una consulta para continuar.')
        return value

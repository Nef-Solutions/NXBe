from rest_framework import serializers

from .models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    visit_id = serializers.IntegerField(read_only=True)
    professional_profile_id = serializers.IntegerField(source='professional_id', read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'visit_id', 'professional_profile_id', 'amount', 'buy_order',
            'status', 'created_at', 'updated_at',
        )

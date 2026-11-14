import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from transbank.error.transbank_error import TransbankError

from .models import PaymentTransaction, ProfessionalSubscriptionPlan
from .serializers import PaymentTransactionSerializer
from .services import (
    cancel_visit_payment,
    confirm_payment,
    create_professional_subscription_payment,
    create_visit_payment,
)


logger = logging.getLogger(__name__)


class VisitPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, visit_id):
        try:
            payment_result, error = create_visit_payment(
                request.user,
                visit_id,
                settings.TRANSBANK_RETURN_URL,
            )
        except TransbankError:
            return Response(
                {'detail': 'No fue posible iniciar el pago en Transbank. Inténtalo nuevamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if error:
            response_status = (
                status.HTTP_404_NOT_FOUND
                if error.startswith('No se encontró')
                else status.HTTP_409_CONFLICT
            )
            return Response({'detail': error}, status=response_status)

        payment, transbank_response = payment_result
        return Response(
            {
                **PaymentTransactionSerializer(payment).data,
                'url': transbank_response['url'],
                'token': transbank_response['token'],
                'environment': 'sandbox',
            },
            status=status.HTTP_201_CREATED,
        )


class VisitPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, visit_id):
        payment = (
            PaymentTransaction.objects.filter(visit_id=visit_id, payer=request.user)
            .first()
        )
        if payment is None:
            return Response(
                {'detail': 'No existe un pago para esta solicitud.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PaymentTransactionSerializer(payment).data)


class ProfessionalSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            payment_result, error = create_professional_subscription_payment(
                request.user,
                settings.TRANSBANK_RETURN_URL,
            )
        except TransbankError:
            return Response(
                {'detail': 'No fue posible iniciar el pago en Transbank. Inténtalo nuevamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if error:
            response_status = (
                status.HTTP_404_NOT_FOUND
                if error.startswith('No se encontró')
                else status.HTTP_403_FORBIDDEN
                if error.startswith('Solo un profesional')
                else status.HTTP_409_CONFLICT
            )
            return Response({'detail': error}, status=response_status)

        payment, transbank_response = payment_result
        return Response(
            {
                **PaymentTransactionSerializer(payment).data,
                'url': transbank_response['url'],
                'token': transbank_response['token'],
                'environment': 'sandbox',
            },
            status=status.HTTP_201_CREATED,
        )


class ProfessionalSubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != request.user.Role.PROFESSIONAL:
            return Response(
                {'detail': 'Solo los profesionales pueden consultar su suscripción.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        professional = getattr(request.user, 'professional_profile', None)
        if professional is None:
            return Response(
                {'detail': 'No se encontró el perfil profesional.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        plan = ProfessionalSubscriptionPlan.objects.filter(is_active=True).first()
        if plan is None:
            return Response(
                {'detail': 'La suscripción profesional no está disponible.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        latest_payment = professional.subscription_payments.first()
        if professional.has_active_subscription:
            subscription_status = 'ACTIVE'
        elif professional.subscription_expires_at:
            subscription_status = 'EXPIRED'
        else:
            subscription_status = 'INACTIVE'
        return Response({
            'professional_profile_id': professional.pk,
            'status': subscription_status,
            'amount': str(plan.amount),
            'plan': {
                'code': plan.code,
                'name': plan.name,
                'duration_months': plan.duration_months,
            },
            'expires_at': professional.subscription_expires_at,
            'latest_payment': (
                PaymentTransactionSerializer(latest_payment).data
                if latest_payment
                else None
            ),
        })


class TransbankReturnView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token_ws')
        if token:
            if not isinstance(token, str) or len(token) > 64:
                return self._redirect('error')
            try:
                payment, error = confirm_payment(token)
            except TransbankError:
                logger.exception('Transbank no pudo confirmar el pago.')
                return self._redirect('error')
            if error or payment is None:
                return self._redirect('error')
            return self._redirect(
                payment.status.lower(),
                payment.visit_id,
                payment.professional_id,
            )

        payment = cancel_visit_payment(request.data.get('TBK_ORDEN_COMPRA'))
        return self._redirect(
            'cancelled',
            payment.visit_id if payment else None,
            payment.professional_id if payment else None,
        )

    def _redirect(self, outcome, visit_id=None, professional_id=None):
        query = {'status': outcome}
        if visit_id is not None:
            query['visit_id'] = visit_id
        if professional_id is not None:
            query['professional_profile_id'] = professional_id
        return HttpResponseRedirect(
            f'{settings.PAYMENT_RESULT_URL}?{urlencode(query)}'
        )

import hashlib
import hmac
import logging
import uuid
import calendar
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction

from apps.authentication.models import ProfessionalProfile, User
from apps.visits.models import VisitRequest
from .models import PaymentTransaction, ProfessionalSubscriptionPlan


logger = logging.getLogger(__name__)
PENDING_PAYMENT_LIFETIME = timedelta(minutes=30)


def webpay_transaction():
    transaction = Transaction.build_for_integration(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
    )
    transaction.options.timeout = 20
    return transaction


def token_digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def create_visit_payment(user, visit_id, return_url):
    with transaction.atomic():
        visit = (
            VisitRequest.objects.select_for_update()
            .select_related('professional')
            .filter(pk=visit_id, client=user)
            .first()
        )
        if visit is None:
            return None, 'No se encontró la solicitud de visita.'
        if visit.status != VisitRequest.Status.ACCEPTED:
            return None, 'Solo puedes pagar una solicitud aceptada por el profesional.'
        if visit.professional.visit_fee <= 0:
            return None, 'El profesional no tiene una tarifa de visita válida.'
        if visit.payments.filter(status=PaymentTransaction.Status.AUTHORIZED).exists():
            return None, 'Esta solicitud ya tiene un pago autorizado.'
        PaymentTransaction.objects.filter(
            visit=visit,
            status=PaymentTransaction.Status.PENDING,
            created_at__lt=timezone.now() - PENDING_PAYMENT_LIFETIME,
        ).update(status=PaymentTransaction.Status.FAILED, updated_at=timezone.now())
        if visit.payments.filter(status=PaymentTransaction.Status.PENDING).exists():
            return None, 'Ya existe un pago pendiente para esta solicitud.'

        payment = PaymentTransaction.objects.create(
            visit=visit,
            payer=user,
            amount=visit.professional.visit_fee,
            buy_order=f'ov-{uuid.uuid4().hex[:23]}',
            session_id=f'ov-{user.pk}-{uuid.uuid4().hex}',
        )

    return _start_payment(payment, return_url)


def create_professional_subscription_payment(user, return_url):
    if user.role != User.Role.PROFESSIONAL:
        return None, 'Solo un profesional puede contratar esta suscripción.'

    with transaction.atomic():
        plan = (
            ProfessionalSubscriptionPlan.objects.select_for_update()
            .filter(is_active=True)
            .first()
        )
        if plan is None:
            return None, 'La suscripción profesional no está disponible.'
        professional = (
            ProfessionalProfile.objects.select_for_update()
            .filter(user=user)
            .first()
        )
        if professional is None:
            return None, 'No se encontró el perfil profesional.'
        PaymentTransaction.objects.filter(
            professional=professional,
            status=PaymentTransaction.Status.PENDING,
            created_at__lt=timezone.now() - PENDING_PAYMENT_LIFETIME,
        ).update(status=PaymentTransaction.Status.FAILED, updated_at=timezone.now())
        if PaymentTransaction.objects.filter(
            professional=professional,
            status=PaymentTransaction.Status.PENDING,
        ).exists():
            return None, 'Ya existe un pago de suscripción pendiente.'

        payment = PaymentTransaction.objects.create(
            professional=professional,
            subscription_plan=plan,
            subscription_duration_months=plan.duration_months,
            payer=user,
            amount=plan.amount,
            buy_order=f'ov-{uuid.uuid4().hex[:23]}',
            session_id=f'ov-{user.pk}-{uuid.uuid4().hex}',
        )

    return _start_payment(payment, return_url)


def _start_payment(payment, return_url):
    try:
        response = webpay_transaction().create(
            payment.buy_order,
            payment.session_id,
            float(payment.amount),
            return_url,
        )
    except TransbankError:
        payment.status = PaymentTransaction.Status.FAILED
        payment.save(update_fields=['status', 'updated_at'])
        logger.exception('Transbank no pudo iniciar el pago %s.', payment.pk)
        raise

    payment.token_hash = token_digest(response['token'])
    payment.save(update_fields=['token_hash', 'updated_at'])
    return (payment, response), None


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def confirm_payment(token):
    digest = token_digest(token)
    with transaction.atomic():
        payment = (
            PaymentTransaction.objects.select_for_update()
            .filter(token_hash=digest)
            .first()
        )
        if payment is None or not hmac.compare_digest(payment.token_hash, digest):
            return None, 'No se encontró una transacción válida.'
        if payment.status == PaymentTransaction.Status.AUTHORIZED:
            return payment, None
        if payment.status != PaymentTransaction.Status.PENDING:
            return None, 'La transacción ya no está pendiente.'

        response = webpay_transaction().commit(token)
        try:
            confirmed_amount = Decimal(str(response.get('amount')))
            response_code = int(response.get('response_code', -1))
        except (InvalidOperation, TypeError, ValueError):
            confirmed_amount = None
            response_code = -1
        if (
            response.get('buy_order') != payment.buy_order
            or response.get('session_id') != payment.session_id
            or confirmed_amount != payment.amount
        ):
            logger.error('La confirmación de Transbank no coincide con el pago %s.', payment.pk)
            return None, 'La confirmación recibida no coincide con el pago.'

        payment.response_code = response_code
        payment.status = (
            PaymentTransaction.Status.AUTHORIZED
            if response_code == 0 and response.get('status') == 'AUTHORIZED'
            else PaymentTransaction.Status.REJECTED
        )
        payment.save(update_fields=['response_code', 'status', 'updated_at'])

        if payment.status == PaymentTransaction.Status.AUTHORIZED and payment.professional_id:
            professional = ProfessionalProfile.objects.select_for_update().get(
                pk=payment.professional_id,
            )
            now = timezone.now()
            subscription_start = professional.subscription_expires_at
            if subscription_start is None or subscription_start <= now:
                subscription_start = now
            professional.subscription_expires_at = _add_months(
                subscription_start,
                payment.subscription_duration_months,
            )
            professional.save(update_fields=['subscription_expires_at'])

        return payment, None


def confirm_visit_payment(token):
    return confirm_payment(token)


def cancel_visit_payment(buy_order):
    if not buy_order:
        return None
    payment = PaymentTransaction.objects.filter(buy_order=buy_order).first()
    if payment and payment.status == PaymentTransaction.Status.PENDING:
        payment.status = PaymentTransaction.Status.REJECTED
        payment.save(update_fields=['status', 'updated_at'])
    return payment

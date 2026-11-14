from django.urls import path

from .views import (
    ProfessionalSubscriptionStatusView,
    ProfessionalSubscriptionView,
    TransbankReturnView,
    VisitPaymentStatusView,
    VisitPaymentView,
)


urlpatterns = [
    path('professional-subscription/', ProfessionalSubscriptionStatusView.as_view(), name='professional-subscription-status'),
    path('professional-subscription/transbank/', ProfessionalSubscriptionView.as_view(), name='professional-subscription-create'),
    path('visits/<int:visit_id>/', VisitPaymentStatusView.as_view(), name='visit-payment-status'),
    path('visits/<int:visit_id>/transbank/', VisitPaymentView.as_view(), name='visit-payment-create'),
    path('transbank/return/', TransbankReturnView.as_view(), name='transbank-return'),
]

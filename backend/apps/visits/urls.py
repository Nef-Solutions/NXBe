from django.urls import path

from .views import ClaimActionView, ClaimListCreateView, ContentProgressCreateView, NotificationListView, NotificationReadView, ProfessionalContentListView, RatingCreateView, TicketListCreateView, TicketResolveView, VisitActionView, VisitListCreateView

urlpatterns = [
    path('requests/', VisitListCreateView.as_view(), name='visit-list-create'),
    path('requests/<int:pk>/<str:action>/', VisitActionView.as_view(), name='visit-action'),
    path('ratings/', RatingCreateView.as_view(), name='rating-create'),
    path('claims/', ClaimListCreateView.as_view(), name='claim-list-create'),
    path('claims/<int:pk>/<str:action>/', ClaimActionView.as_view(), name='claim-action'),
    path('tickets/', TicketListCreateView.as_view(), name='ticket-list-create'),
    path('tickets/<int:pk>/resolve/', TicketResolveView.as_view(), name='ticket-resolve'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification-read'),
    path('professional-center/content/', ProfessionalContentListView.as_view(), name='content-list'),
    path('professional-center/progress/', ContentProgressCreateView.as_view(), name='content-progress'),
]
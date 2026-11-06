from django.urls import path

from .views import AvailabilityView, ProfessionalSearchView, TradeDetailView, TradeListCreateView

urlpatterns = [
    path('search/', ProfessionalSearchView.as_view(), name='professional-search-by-prefix'),
    path('me/availability/', AvailabilityView.as_view(), name='professional-availability'),
    path('me/trades/', TradeListCreateView.as_view(), name='professional-trades'),
    path('me/trades/<int:pk>/', TradeDetailView.as_view(), name='professional-trade-detail'),
]

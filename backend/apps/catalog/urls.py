from django.urls import path

from .views import AvailabilityView, CategoryListView, CommuneListView, HomeZoneListView, ProfessionalDetailView, ProfessionalSearchView, SpecialtyListView, TradeDetailView, TradeListCreateView

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('specialties/', SpecialtyListView.as_view(), name='specialty-list'),
    path('zones/', HomeZoneListView.as_view(), name='home-zone-list'),
    path('communes/', CommuneListView.as_view(), name='commune-list'),
    path('professionals/', ProfessionalSearchView.as_view(), name='professional-search'),
    path('professionals/<int:pk>/', ProfessionalDetailView.as_view(), name='professional-detail'),
    path('professionals/me/availability/', AvailabilityView.as_view(), name='professional-availability'),
    path('professionals/me/trades/', TradeListCreateView.as_view(), name='professional-trades'),
    path('professionals/me/trades/<int:pk>/', TradeDetailView.as_view(), name='professional-trade-detail'),
]
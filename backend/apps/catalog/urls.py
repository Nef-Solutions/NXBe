from django.urls import path

from .views import ProfessionalDetailView, ProfessionalSearchView

urlpatterns = [
    path('professionals/', ProfessionalSearchView.as_view(), name='professional-search'),
    path('professionals/<int:pk>/', ProfessionalDetailView.as_view(), name='professional-detail'),
]
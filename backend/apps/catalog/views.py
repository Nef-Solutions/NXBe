from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination

from apps.authentication.models import ProfessionalProfile, User
from .serializers import ProfessionalDetailSerializer, ProfessionalResultSerializer
from .services import ProfessionalSearchService


class ProfessionalSearchPagination(PageNumberPagination):
	page_size = 20
	page_size_query_param = 'page_size'
	max_page_size = 50


class ProfessionalSearchView(ListAPIView):
	serializer_class = ProfessionalResultSerializer
	pagination_class = ProfessionalSearchPagination

	def get_queryset(self):
		return ProfessionalSearchService.search(
			keyword=self.request.query_params.get('keyword'),
			zone_id=self.request.query_params.get('zone_id'),
			category_id=self.request.query_params.get('category_id'),
		)


class ProfessionalDetailView(RetrieveAPIView):
	serializer_class = ProfessionalDetailSerializer
	queryset = ProfessionalProfile.objects.filter(
		verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
		user__account_status=User.AccountStatus.ACTIVE,
	).select_related('user').prefetch_related('specialties', 'trades')
from django.shortcuts import render

# Create your views here.

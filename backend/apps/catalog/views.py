from decimal import Decimal, InvalidOperation

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from apps.authentication.models import ProfessionalProfile, User
from .models import HomeZone, ProfessionalTrade, Specialty, TradeCategory
from .serializers import CategorySerializer, HomeZoneSerializer, ProfessionalDetailSerializer, ProfessionalResultSerializer, SpecialtySerializer, TradeSerializer
from .services import ProfessionalSearchService


class ProfessionalSearchPagination(PageNumberPagination):
	page_size = 20
	page_size_query_param = 'page_size'
	max_page_size = 50


class ProfessionalSearchView(ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = ProfessionalResultSerializer
	pagination_class = ProfessionalSearchPagination

	def get_queryset(self):
		return ProfessionalSearchService.search(
			keyword=self.request.query_params.get('keyword'),
			zone_id=self.request.query_params.get('zone_id'),
			category_id=self.request.query_params.get('category_id'),
			specialty_id=self.request.query_params.get('specialty_id'),
			commune=self.request.query_params.get('commune'),
			latitude=self.request.query_params.get('latitude'),
			longitude=self.request.query_params.get('longitude'),
			radius=self.request.query_params.get('radius'),
		)


class ProfessionalDetailView(RetrieveAPIView):
	permission_classes = [AllowAny]
	serializer_class = ProfessionalDetailSerializer
	queryset = ProfessionalProfile.objects.filter(
		verification_status=ProfessionalProfile.VerificationStatus.APPROVED,
		user__account_status=User.AccountStatus.ACTIVE,
	).select_related('user').prefetch_related('specialties', 'trades')


class CategoryListView(ListAPIView):
	permission_classes = [AllowAny]
	queryset = TradeCategory.objects.prefetch_related('home_zones')
	serializer_class = CategorySerializer


class SpecialtyListView(ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = SpecialtySerializer

	def get_queryset(self):
		queryset = Specialty.objects.all()
		if self.request.query_params.get('category_id'):
			queryset = queryset.filter(category_id=self.request.query_params['category_id'])
		return queryset


class HomeZoneListView(ListAPIView):
	permission_classes = [AllowAny]
	queryset = HomeZone.objects.all()
	serializer_class = HomeZoneSerializer


class CommuneListView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		communes = ProfessionalProfile.objects.filter(
			verification_status=ProfessionalProfile.VerificationStatus.APPROVED
		).values_list('coverage_communes', flat=True)
		return Response(sorted({commune for values in communes for commune in (values or [])}))


class AvailabilityView(APIView):
	permission_classes = [IsAuthenticated]

	def get_profile(self, request):
		if request.user.role != User.Role.PROFESSIONAL:
			return None
		return ProfessionalProfile.objects.get(user=request.user)

	def get(self, request):
		profile = self.get_profile(request)
		if profile is None:
			return Response({'detail': 'Solo los profesionales pueden gestionar su disponibilidad.'}, status=403)
		return Response({
			'work_days': profile.work_days, 'work_start': profile.work_start,
			'work_end': profile.work_end, 'is_available': profile.is_available,
			'coverage_communes': profile.coverage_communes,
		})

	def patch(self, request):
		profile = self.get_profile(request)
		if profile is None:
			return Response({'detail': 'Solo los profesionales pueden gestionar su disponibilidad.'}, status=403)
		allowed = ('work_days', 'work_start', 'work_end', 'is_available', 'coverage_communes')
		for field in allowed:
			if field in request.data:
				setattr(profile, field, request.data[field])
		changed_fields = [field for field in allowed if field in request.data]
		if 'latitude' in request.data or 'longitude' in request.data:
			if 'latitude' not in request.data or 'longitude' not in request.data:
				return Response({'detail': 'latitude y longitude deben enviarse juntas.'}, status=400)
			try:
				latitude = Decimal(str(request.data['latitude'])).quantize(Decimal('0.00001'))
				longitude = Decimal(str(request.data['longitude'])).quantize(Decimal('0.00001'))
			except (InvalidOperation, TypeError, ValueError):
				return Response({'detail': 'Las coordenadas deben ser numéricas.'}, status=400)
			if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
				return Response({'detail': 'Las coordenadas están fuera de rango.'}, status=400)
			profile.service_latitude = latitude
			profile.service_longitude = longitude
			changed_fields.extend(['service_latitude', 'service_longitude'])
		if changed_fields:
			profile.save(update_fields=changed_fields)
		return self.get(request)


class TradeListCreateView(APIView):
	permission_classes = [IsAuthenticated]

	def get_profile(self, request):
		if request.user.role != User.Role.PROFESSIONAL:
			return None
		return ProfessionalProfile.objects.get(user=request.user)

	def get(self, request):
		profile = self.get_profile(request)
		if profile is None:
			return Response({'detail': 'Solo los profesionales pueden gestionar oficios.'}, status=403)
		return Response(TradeSerializer(profile.trades.all(), many=True).data)

	def post(self, request):
		profile = self.get_profile(request)
		if profile is None:
			return Response({'detail': 'Solo los profesionales pueden gestionar oficios.'}, status=403)
		serializer = TradeSerializer(data=request.data, context={'professional': profile})
		serializer.is_valid(raise_exception=True)
		return Response(TradeSerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


class TradeDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get_object(self, request, pk):
		return ProfessionalTrade.objects.get(pk=pk, professional__user=request.user)

	def patch(self, request, pk):
		trade = self.get_object(request, pk)
		serializer = TradeSerializer(trade, data=request.data, partial=True, context={'professional': trade.professional})
		serializer.is_valid(raise_exception=True)
		return Response(TradeSerializer(serializer.save()).data)

	def delete(self, request, pk):
		trade = self.get_object(request, pk)
		trade.is_active = False
		trade.save(update_fields=['is_active'])
		return Response(status=status.HTTP_204_NO_CONTENT)
from django.shortcuts import render

# Create your views here.

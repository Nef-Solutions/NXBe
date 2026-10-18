from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import AccountStatusView, ChangePasswordView, LoginView, MeView, OverolPasswordResetView, OverolTokenObtainPairView, LogoutView, RegisterView, VerificationDecisionView, VerificationMessageListCreateView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', OverolTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
    path('password/reset/', OverolPasswordResetView.as_view(), name='password-reset'),
    path('verification/messages/', VerificationMessageListCreateView.as_view(), name='verification-messages'),
    path('verification/<int:pk>/<str:decision>/', VerificationDecisionView.as_view(), name='verification-decision'),
    path('admin/accounts/<int:pk>/status/', AccountStatusView.as_view(), name='account-status'),
]
from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import *

urlpatterns = [
    
    path("register/", RegisterAPIView.as_view()),
    path("verify-email/", VerifyOTPAPIView.as_view()),
    path("resend-otp/", ResendOTPAPIView.as_view()),
    path("login/", LoginAPIView.as_view()),
    
    path("profile/", ProfileAPIView.as_view()),
    path("update-profile/", UpdateProfileAPIView.as_view()),
    
    path("forgot-password/", ForgotPasswordAPIView.as_view()),
    path("resend-reset-otp/", ResendResetOTPAPIView.as_view()),
    path("verify-reset-otp/", VerifyResetOTPAPIView.as_view()),
    path("reset-password/", ResetPasswordAPIView.as_view()),
    # Send OTP using email or mobile
    path("send-login-otp/", SendLoginOTPAPIView.as_view()),
    # Verify OTP and register/login the user
    path("verify-login-otp/", VerifyLoginOTPAPIView.as_view()),
    
    path("logout/", LogoutAPIView.as_view()),
    # Get a new access token using the refresh token
    path("token/refresh/", TokenRefreshView.as_view()),


    
    path("users/list/", AdminUserListAPIView.as_view()),
    path("users/detail/", AdminUserDetailAPIView.as_view()),
    path("users/activate/", AdminActivateUserAPIView.as_view()),
    path("users/deactivate/", AdminDeactivateUserAPIView.as_view()),
]

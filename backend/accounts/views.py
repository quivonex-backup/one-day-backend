from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .serializers import RegisterSerializer, LoginSerializer
from .models import User, OTPVerification
from accounts.serializers import *
from .utils import (
    blacklist_all_refresh_tokens,
    check_otp,
    create_email_otp,
    create_password_reset_otp,
    send_email_otp,
)
from .access import is_admin

class RegisterAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []
    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegisterSuccessResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
        tags=["Accounts - Authentication"],
        summary="Register a normal user account",
    )
    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Registration successful. OTP sent to your email."
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "success": False,
                "message": "Validation Error",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
class LoginAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []
    @extend_schema(
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name="LoginSuccessResponse",
                fields={
                    "success": serializers.BooleanField(),
                    "message": serializers.CharField(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                    "user": inline_serializer(
                        name="LoginUserData",
                        fields={
                            "id": serializers.IntegerField(),
                            "email": serializers.EmailField(),
                            "is_admin": serializers.BooleanField(),
                        },
                    ),
                    "data": inline_serializer(
                        name="LoginTokenData",
                        fields={
                            "access": serializers.CharField(),
                            "refresh": serializers.CharField(),
                            "is_admin": serializers.BooleanField(),
                            "email": serializers.EmailField(),
                            "id": serializers.IntegerField(),
                            "user": inline_serializer(
                                name="LoginNestedUserData",
                                fields={
                                    "id": serializers.IntegerField(),
                                    "email": serializers.EmailField(),
                                    "is_admin": serializers.BooleanField(),
                                },
                            ),
                        },
                    ),
                },
            )
        },
        tags=["Accounts - Authentication"],
        summary="Login and receive JWT tokens",
    )
    def post(self, request):

        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():

            user = serializer.validated_data["user"]

            refresh = RefreshToken.for_user(user)

            user_data = {
                "id": user.id,
                "email": user.email,
                "is_admin": is_admin(user),
            }

            return Response(
                {
                    "success": True,
                    "message": "Login successful.",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": user_data,
                    "data": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "is_admin": is_admin(user),
                        "email": user.email,
                        "id": user.id,
                        "user": user_data,
                    }
                }
            )

        return Response(
            {
                "success": False,
                "message": "Invalid Credentials",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
        
from .models import UserProfile

class ProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=None,
        responses={200: None},
        tags=["Accounts - Profile"],
        summary="Get authenticated user profile",
    )
    def post(self, request):

        profile, created = UserProfile.objects.get_or_create(
            user=request.user
        )

        serializer = ProfileSerializer(profile)

        return Response(
            {
                "success": True,
                "message": "Profile fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )        



class UpdateProfileAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=ProfileSerializer,
        responses={200: None},
        tags=["Accounts - Profile"],
        summary="Update authenticated user profile",
    )

    def post(self, request):

        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        serializer = ProfileSerializer(profile, data=request.data, partial=True,)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Profile updated successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

# ==========================================
# EMAIL VERIFICATION + PASSWORD RESET (OTP)
# ==========================================
# Security rules:
# - OTPs are stored hashed and can be used only once.
# - Max 5 wrong guesses per OTP, then a new OTP is needed.
# - A new OTP can be requested once every 60 seconds.
# - Responses never reveal whether an email is registered.

RESEND_MESSAGE = (
    "If this email needs verification, a new OTP has been sent. "
    "You can request a new OTP once every 60 seconds."
)

RESET_MESSAGE = (
    "If an account exists for this email, a password reset OTP has been sent. "
    "You can request a new OTP once every 60 seconds."
)


def get_user_by_email(email):
    return User.objects.filter(email__iexact=str(email or "").strip()).first()


def get_resettable_user(email):
    """Only active, email-verified users can reset their password."""
    user = get_user_by_email(email)
    if user and user.is_active and user.is_email_verified:
        return user
    return None


def otp_error_response(message):
    return Response(
        {"success": False, "message": message},
        status=status.HTTP_400_BAD_REQUEST,
    )


def serializer_error_response(serializer):
    return Response(
        {"success": False, "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


class VerifyOTPAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: None},
        tags=["Accounts - Authentication"],
        summary="Verify email OTP",
    )
    def post(self, request):

        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer)

        user = get_user_by_email(serializer.validated_data["email"])

        error = check_otp(
            user,
            OTPVerification.OTPType.EMAIL_VERIFICATION,
            serializer.validated_data["otp"],
            consume=True,
        )
        if error:
            return otp_error_response(error)

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        return Response(
            {"success": True, "message": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


class ResendOTPAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []

    @extend_schema(
        request=ResendOTPSerializer,
        responses={200: None},
        tags=["Accounts - Authentication"],
        summary="Resend email verification OTP",
    )
    def post(self, request):

        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer)

        user = get_user_by_email(serializer.validated_data["email"])

        if user and user.is_active and not user.is_email_verified:
            otp = create_email_otp(user)
            if otp:
                send_email_otp(user.email, otp)

        # Same answer for every email.
        return Response(
            {"success": True, "message": RESEND_MESSAGE},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: None},
        tags=["Accounts - Password"],
        summary="Request password reset OTP",
    )
    def post(self, request):

        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer)

        user = get_resettable_user(serializer.validated_data["email"])

        if user:
            otp = create_password_reset_otp(user)
            if otp:
                send_email_otp(user.email, otp, purpose="reset")

        # Same answer for every email.
        return Response(
            {"success": True, "message": RESET_MESSAGE},
            status=status.HTTP_200_OK,
        )


class ResendResetOTPAPIView(ForgotPasswordAPIView):
    """Resending a reset OTP works exactly like forgot password."""
    pass


class VerifyResetOTPAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []

    @extend_schema(
        request=VerifyResetOTPSerializer,
        responses={200: None},
        tags=["Accounts - Password"],
        summary="Verify password reset OTP",
    )
    def post(self, request):

        serializer = VerifyResetOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer)

        user = get_resettable_user(serializer.validated_data["email"])

        # Keep the OTP so the reset-password step can use it.
        error = check_otp(
            user,
            OTPVerification.OTPType.PASSWORD_RESET,
            serializer.validated_data["otp"],
            consume=False,
        )
        if error:
            return otp_error_response(error)

        return Response(
            {"success": True, "message": "OTP verified successfully."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPIView(APIView):

    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = []

    @extend_schema(
        request=ResetPasswordSerializer,
        responses={200: None},
        tags=["Accounts - Password"],
        summary="Reset user password",
    )
    def post(self, request):

        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer)

        user = get_resettable_user(serializer.validated_data["email"])

        # OTP is checked again here and then deleted (one-time use).
        error = check_otp(
            user,
            OTPVerification.OTPType.PASSWORD_RESET,
            serializer.validated_data["otp"],
            consume=True,
        )
        if error:
            return otp_error_response(error)

        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])

        # Log out every device that used the old password.
        blacklist_all_refresh_tokens(user)

        return Response(
            {"success": True, "message": "Password reset successfully. Please log in again."},
            status=status.HTTP_200_OK,
        )



from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class LogoutAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: None},
        tags=["Accounts - Authentication"],
        summary="Logout and blacklist refresh token",
    )
    
    def post(self, request):

        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data["refresh"]

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {
                    "success": True,
                    "message": "Logged out successfully."
                },
                status=status.HTTP_200_OK
            )

        except TokenError:
            return Response(
                {
                    "success": False,
                    "message": "Invalid or expired refresh token."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Something went wrong while logging out."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        
        
        
class AdminUserListAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=inline_serializer(
            name="AdminUserListRequest",
            fields={
                "search": serializers.CharField(required=False),
                "is_active": serializers.BooleanField(required=False),
                "is_email_verified": serializers.BooleanField(required=False),
                "is_mobile_verified": serializers.BooleanField(required=False),
                "page": serializers.IntegerField(required=False),
                "page_size": serializers.IntegerField(required=False),
            },
        ),
        responses={200: None},
        tags=["Accounts - Admin"],
        summary="List and filter users",
    )

    def post(self, request):

        # -----------------------------
        # Admin permission
        # -----------------------------

        if not is_admin(request.user):

            return Response(
                {
                    "success": False,
                    "message": "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # -----------------------------
        # Query parameters
        # -----------------------------

        search = request.data.get("search", "").strip()

        is_active = request.data.get("is_active")

        is_email_verified = request.data.get(
            "is_email_verified"
        )

        is_mobile_verified = request.data.get(
            "is_mobile_verified"
        )

        # -----------------------------
        # Base queryset
        # -----------------------------

        users = User.objects.all().order_by("-created_at")

        # -----------------------------
        # Search
        # -----------------------------

        if search:

            users = users.filter(
                Q(email__icontains=search)
                |
                Q(mobile_number__icontains=search)
            )

        # -----------------------------
        # -----------------------------
        # Active filter
        # -----------------------------

        if is_active is not None:

            users = users.filter(
                is_active=is_active
            )

        # -----------------------------
        # Email verification
        # -----------------------------

        if is_email_verified is not None:

            users = users.filter(
                is_email_verified=is_email_verified
            )

        # -----------------------------
        # Mobile verification
        # -----------------------------

        if is_mobile_verified is not None:

            users = users.filter(
                is_mobile_verified=is_mobile_verified
            )

        # -----------------------------
        # Pagination
        # -----------------------------

        page = int(
            request.data.get("page", 1)
        )

        page_size = int(
            request.data.get("page_size", 20)
        )

        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 20

        if page_size > 100:
            page_size = 100

        total_users = users.count()

        start = (page - 1) * page_size

        end = start + page_size

        users = users[start:end]

        # -----------------------------
        # Response data
        # -----------------------------

        data = []

        for user in users:

            data.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "mobile_number": user.mobile_number,
                    "is_admin": is_admin(user),
                    "is_email_verified": user.is_email_verified,
                    "is_mobile_verified": user.is_mobile_verified,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                }
            )

        return Response(
            {
                "success": True,
                "count": total_users,
                "page": page,
                "page_size": page_size,
                "total_pages": (
                    (total_users + page_size - 1)
                    // page_size
                ),
                "data": data
            },
            status=status.HTTP_200_OK
        )
        
        
        
class AdminUserDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=inline_serializer(
            name="AdminUserDetailRequest",
            fields={
                "user_id": serializers.IntegerField(),
            },
        ),
        responses={200: None},
        tags=["Accounts - Admin"],
        summary="Get user details",
    )
    def post(self, request):

        if not is_admin(request.user):
            return Response(
                {
                    "success": False,
                    "message": "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {
                    "success": False,
                    "message": "User ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            "id": user.id,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "is_admin": is_admin(user),
            "is_email_verified": user.is_email_verified,
            "is_mobile_verified": user.is_mobile_verified,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

        return Response(
            {
                "success": True,
                "data": data
            },
            status=status.HTTP_200_OK
        )
        

        
class AdminActivateUserAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=inline_serializer(
            name="AdminActivateUserRequest",
            fields={
                "user_id": serializers.IntegerField(),
            },
        ),
        responses={200: None},
        tags=["Accounts - Admin"],
        summary="Activate user",
    )
    def post(self, request):

        if not is_admin(request.user):
            return Response(
                {
                    "success": False,
                    "message": "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {
                    "success": False,
                    "message": "User ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "User is already active."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "User activated successfully."
            },
            status=status.HTTP_200_OK
        )
        
        
        
        
class AdminDeactivateUserAPIView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=inline_serializer(
            name="AdminDeactivateUserRequest",
            fields={
                "user_id": serializers.IntegerField(),
            },
        ),
        responses={200: None},
        tags=["Accounts - Admin"],
        summary="Deactivate user",
    )

    def post(self, request):

        if not is_admin(request.user):
            return Response(
                {
                    "success": False,
                    "message": "Permission denied."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {
                    "success": False,
                    "message": "User ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "User not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if user.id == request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "You cannot deactivate your own account."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "User is already inactive."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "success": True,
                "message": "User deactivated successfully."
            },
            status=status.HTTP_200_OK
        )
        

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError

from .serializers import SendLoginOTPSerializer
from .otp_services import create_login_otp
from .otp_delivery import deliver_login_otp


class SendLoginOTPAPIView(APIView):
    
    # Public OTP endpoint: no JWT required
    authentication_classes = []
    throttle_scope = "auth"
    permission_classes = [AllowAny]

    def post(self, request):

        # Validate email or mobile number
        serializer = SendLoginOTPSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        channel = serializer.validated_data["channel"]

        # Generate secure OTP
        otp = create_login_otp(
            identifier=identifier,
            channel=channel
        )

        # Send OTP by email or SMS
        deliver_login_otp(
            identifier=identifier,
            channel=channel,
            otp=otp
        )

        return Response(
            {
                "success": True,
                "message": "OTP sent successfully.",
                "channel": channel
            },
            status=status.HTTP_200_OK
        )

        
#############################################

from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserProfile
from .serializers import VerifyLoginOTPSerializer
from .otp_services import verify_login_otp


class VerifyLoginOTPAPIView(APIView):

    # OTP verification is public; do not inspect stale JWT headers.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):

        # Validate the email/mobile and OTP
        serializer = VerifyLoginOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        channel = serializer.validated_data["channel"]
        otp = serializer.validated_data["otp"]

        # Find an existing account using the selected contact
        if channel == "EMAIL":
            lookup = {"email": identifier}
        else:
            lookup = {"mobile_number": identifier}

        # Verify the OTP before creating or logging into an account
        verify_login_otp(identifier, channel, otp)

        with transaction.atomic():

            # Create a new account if necessary
            user, created = User.objects.get_or_create(**lookup)

            # Disabled accounts cannot log in or update verification flags.
            if not user.is_active:
                return Response(
                    {"success": False, "message": "This account is inactive."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
                UserProfile.objects.get_or_create(user=user)

            # Mark the selected contact as verified
            if channel == "EMAIL":
                user.is_email_verified = True
                user.save(update_fields=["is_email_verified"])
            else:
                user.is_mobile_verified = True
                user.save(update_fields=["is_mobile_verified"])

        # Generate JWT access and refresh tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": (
                    "Registration successful."
                    if created else "Login successful."
                ),
                "is_new_user": created,
                "user_id": user.id,
                "is_admin": is_admin(user),
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK
        )


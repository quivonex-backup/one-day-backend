from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from common.models import PostalLocation, Skill
from common.serializers import PincodePostalLocationSerializer
from rest_framework import serializers
from pathlib import Path
from .models import User, UserProfile
from .utils import create_email_otp, send_email_otp

class RegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=150)
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"}
    )

    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "email",
            "mobile_number",
            "full_name",
            "password",
            "confirm_password",
        )

    def validate_email(self, value):

        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already registered."
            )

        return value

    def validate_mobile_number(self, value):

        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError(
                "Mobile number already registered."
            )

        return value

    
    def validate(self, attrs):

        # Check that both passwords match.
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        # Validate password strength.
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError({
                "password": list(e.messages)
            })

        return attrs


    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password", None)

        password = validated_data.pop("password")

        full_name = validated_data.pop("full_name", "").strip()
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        UserProfile.objects.create(user=user, full_name=full_name)

        otp = create_email_otp(user)
        send_email_otp(user.email, otp)

        return user
    
    
class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"}
    )

    def validate(self, attrs):

        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        user = authenticate(
            username=email,
            password=password
        )

        # Check credentials first
        if user is None:
            raise serializers.ValidationError({
                "email": "Invalid email or password."
            })

        # Check account status
        if not user.is_active:
            raise serializers.ValidationError({
                "email": "Your account is inactive."
            })

        # Check email verification
        if not user.is_email_verified:
            raise serializers.ValidationError({
                "email": "Please verify your email before logging in."
            })

        attrs["user"] = user

        return attrs
    
    
    
    
    
class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    mobile_number = serializers.CharField(
        source="user.mobile_number",
        read_only=True,
    )

    is_admin = serializers.SerializerMethodField()

    # User selects a post office/village returned by pincode lookup API.
    postal_location_id = serializers.PrimaryKeyRelatedField(
        source="postal_location",
        queryset=PostalLocation.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )

    # Full selected post-office/village details in profile response.
    postal_location = PincodePostalLocationSerializer(
        read_only=True,
    )

    # Accept and return active Skill IDs.
    # Example request: "skills": [1, 4, 7]
    skills = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.filter(is_active=True),
        required=False,
    )

    def get_is_admin(self, profile):
        return (
            profile.user.is_staff
            or profile.user.is_superuser
        )

    def validate_expected_wage(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Expected wage must be greater than zero."
            )

        return value
    
    def validate_resume(self, value):
        if not value:
            return value

        allowed_extensions = {".pdf", ".doc", ".docx"}
        extension = Path(value.name).suffix.lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Upload a PDF, DOC, or DOCX resume only."
            )

        max_size = 5 * 1024 * 1024  # 5 MB

        if value.size > max_size:
            raise serializers.ValidationError(
                "Resume file size must not exceed 5 MB."
            )

        return value

    def validate(self, attrs):
        # A wage and its type must be saved together.
        expected_wage = attrs.get(
            "expected_wage",
            getattr(self.instance, "expected_wage", None),
        )

        expected_wage_type = attrs.get(
            "expected_wage_type",
            getattr(self.instance, "expected_wage_type", ""),
        )

        if expected_wage is not None and not expected_wage_type:
            raise serializers.ValidationError({
                "expected_wage_type": (
                    "Select DAILY or MONTHLY for the expected wage."
                )
            })

        if expected_wage is None and expected_wage_type:
            raise serializers.ValidationError({
                "expected_wage": (
                    "Enter an expected wage."
                )
            })

        return attrs

    def update(self, instance, validated_data):
        selected_postal_location = validated_data.get(
            "postal_location",
        )

        # Copy official postal data into the normal profile fields.
        if selected_postal_location:
            validated_data["pincode"] = (
                selected_postal_location.pincode
            )
            validated_data["state"] = (
                selected_postal_location.state_name
            )
            validated_data["city"] = (
                selected_postal_location.district_name
            )

        return super().update(instance, validated_data)

    class Meta:
        model = UserProfile

        fields = (
            # Basic profile
            "full_name",
            "profile_picture",
            "resume",
            "gender",
            "date_of_birth",

            # Location
            "address",
            "state",
            "city",
            "pincode",
            "postal_location_id",
            "postal_location",

            # Work details
            "skills",
            "experience_years",
            "expected_wage",
            "expected_wage_type",

            # Optional business and public details
            "about",
            "business_name",

            # Account details
            "email",
            "mobile_number",
            "is_admin",
        )

        read_only_fields = (
            "state",
            "city",
            "pincode",
        )    
    
    
class VerifyOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6
    )

    def validate_otp(self, value):

        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain only digits."
            )

        return value
        
    
class ResendOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()

    # Do not reveal whether an account exists for this email.
    def validate_email(self, value):
        return value.lower().strip()


class ForgotPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

    # Do not reveal whether an account exists for this email.
    def validate_email(self, value):
        return value.lower().strip()
    
    
    
class VerifyResetOTPSerializer(serializers.Serializer):

    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6
    )

    def validate_otp(self, value):

        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain only digits."
            )

        return value
    
    
    
class ResetPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

    otp = serializers.CharField(max_length=6)

    password = serializers.CharField( write_only=True, min_length=8)

    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, attrs):

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        try:
            validate_password(attrs["password"])

        except DjangoValidationError as e:

            raise serializers.ValidationError({
                "password": list(e.messages)
            })

        return attrs
    
    
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()




from .models import LoginOTPChallenge
from .otp_services import normalize_otp_identifier


class SendLoginOTPSerializer(serializers.Serializer):

    # User selects email or mobile OTP
    channel = serializers.ChoiceField(
        choices=LoginOTPChallenge.Channel.choices
    )

    identifier = serializers.CharField(max_length=254)

    def validate(self, attrs):

        # Validate the selected email or mobile number
        attrs["identifier"] = normalize_otp_identifier(
            attrs["identifier"],
            attrs["channel"]
        )

        return attrs




class VerifyLoginOTPSerializer(serializers.Serializer):

    # User selects email or mobile OTP
    channel = serializers.ChoiceField(
        choices=LoginOTPChallenge.Channel.choices
    )

    identifier = serializers.CharField(max_length=254)

    otp = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Enter a valid 6-digit OTP."
        }
    )

    def validate(self, attrs):

        # Validate and normalize the email/mobile
        attrs["identifier"] = normalize_otp_identifier(
            attrs["identifier"],
            attrs["channel"]
        )

        return attrs



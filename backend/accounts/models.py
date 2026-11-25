from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from common.models import PostalLocation, Skill
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    # Every account is a normal user. Django's is_staff/is_superuser flags
    # are the only source of administration access.
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )

    mobile_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )

    is_email_verified = models.BooleanField(default=False)

    is_mobile_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)

    last_login = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["mobile_number"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email or self.mobile_number or str(self.pk)
    
    
class UserProfile(models.Model):

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Basic profile
    full_name = models.CharField(max_length=150, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )
    resume = models.FileField(
        upload_to="resumes/",
        blank=True,
        null=True,
    )
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # Contact and location
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    postal_location = models.ForeignKey(PostalLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles",)
    
    # Work details — used when the user applies for jobs.
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="user_profiles",
    )

    experience_years = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    expected_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class WageType(models.TextChoices):
        DAILY = "DAILY", "Daily"
        MONTHLY = "MONTHLY", "Monthly"

    expected_wage_type = models.CharField(
        max_length=10,
        choices=WageType.choices,
        blank=True,
    )
    
    # Shared profile details
    about = models.TextField(blank=True)

    # Optional: used when the same user posts jobs for a business.
    business_name = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name or self.user.email or str(self.user_id)
    
    
    
    
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

class OTPVerification(models.Model):

    class OTPType(models.TextChoices):
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Email Verification"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"

        # OTP-based registration and login
        LOGIN = "LOGIN", "Login"
        REGISTRATION = "REGISTRATION", "Registration"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")

        # Stores only the hashed OTP, never the plain 6 digits.
    otp = models.CharField(max_length=128)

    otp_type = models.CharField(max_length=30, choices=OTPType.choices)

    is_verified = models.BooleanField(default=False)

    # Wrong guesses for this OTP. Blocked after MAX_OTP_ATTEMPTS.
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_verifications"
        ordering = ["-created_at"]
        
        indexes = [
        models.Index(fields=["user"]),
        models.Index(fields=["otp_type"]),]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.email} - {self.otp_type}"
    
#################################################################################

class LoginOTPChallenge(models.Model):

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        MOBILE = "MOBILE", "Mobile"

    # Email or mobile number requesting OTP
    identifier = models.CharField(
        max_length=254,
        db_index=True
    )

    # Where the OTP will be delivered
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices
    )

    # Store hashed OTP, not the actual OTP
    otp_hash = models.CharField(max_length=128)

    expires_at = models.DateTimeField()

    # Count incorrect OTP attempts
    failed_attempts = models.PositiveIntegerField(default=0)

    # Prevent reusing a verified OTP
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_otp_challenges"
        ordering = ["-created_at"]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.channel} OTP request - {self.pk}"

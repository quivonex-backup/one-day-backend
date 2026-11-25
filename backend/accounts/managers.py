
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(
        self,
        email=None,
        mobile_number=None,
        password=None,
        **extra_fields
    ):

        # Email or mobile number is compulsory
        if not email and not mobile_number:
            raise ValueError(
                "Either email or mobile number is required."
            )

        # Normalize the provided email
        if email:
            email = self.normalize_email(email).strip().lower()
        else:
            email = None

        # Normalize the provided mobile number
        if mobile_number:
            mobile_number = str(mobile_number).strip()
        else:
            mobile_number = None

        # Create one user account
        user = self.model(
            email=email,
            mobile_number=mobile_number,
            **extra_fields
        )

        # OTP users do not need a password
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        mobile_number=None,
        password=None,
        **extra_fields
    ):

        # Admin must use email and password
        if not email:
            raise ValueError("Admin email is required.")

        if not password:
            raise ValueError("Admin password is required.")

        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_active"] = True
        extra_fields["is_email_verified"] = True

        return self.create_user(
            email=email,
            mobile_number=mobile_number,
            password=password,
            **extra_fields
        )


from django.db import models
from django.conf import settings
from applications.models import JobApplication


class Review(models.Model):

    class ReviewType(models.TextChoices):
        # Stored values stay unchanged so existing reviews remain valid.
        APPLICANT_TO_POSTER = "EMPLOYEE_TO_EMPLOYER", "Applicant to job poster"
        POSTER_TO_APPLICANT = "EMPLOYER_TO_EMPLOYEE", "Job poster to applicant"

    # Review must belong to a job application.
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.PROTECT,
        related_name="reviews"
    )

    # Person giving the review.
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_given"
    )

    review_type = models.CharField(
        max_length=30,
        choices=ReviewType.choices
    )

    rating = models.PositiveSmallIntegerField()

    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "reviews"

        constraints = [
            # One review per user per application.
            models.UniqueConstraint(
                fields=["application", "reviewer"],
                name="unique_application_reviewer"
            ),

            # Ratings must be between 1 and 5.
            models.CheckConstraint(
                condition=(
                    models.Q(rating__gte=1) &
                    models.Q(rating__lte=5)
                ),
                name="review_rating_between_1_and_5"
            ),
        ]

    def __str__(self):
        return f"{self.reviewer_id} - {self.rating}/5"

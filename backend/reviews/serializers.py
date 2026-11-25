
from rest_framework import serializers

from applications.models import JobApplication
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Review
        fields = (
            "id",
            "application",
            "reviewer",
            "review_type",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "reviewer",
            "review_type",
            "created_at",
            "updated_at",
        )

    def validate_rating(self, value):

        # Rating must be between 1 and 5.
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )

        return value

    def validate(self, attrs):

        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        user = request.user
        application = attrs["application"]

        # Only completed applications can be reviewed.
        if application.status != JobApplication.Status.COMPLETED:
            raise serializers.ValidationError({
                "application": "Only completed applications can be reviewed."
            })

        if not application.is_active:
            raise serializers.ValidationError({
                "application": "Application is not active."
            })

        # Either participant can review after the work is completed.
        if user.id not in {application.applicant_id, application.job.posted_by_id}:
            raise serializers.ValidationError({
                "application": "You cannot review this application."
            })

        # Prevent duplicate reviews.
        if Review.objects.filter(
            application=application,
            reviewer=user
        ).exists():
            raise serializers.ValidationError({
                "application": "You have already reviewed this application."
            })

        return attrs

    def create(self, validated_data):

        user = self.context["request"].user

        if user.id == validated_data["application"].applicant_id:
            review_type = Review.ReviewType.APPLICANT_TO_POSTER
        else:
            review_type = Review.ReviewType.POSTER_TO_APPLICANT

        return Review.objects.create(
            reviewer=user,
            review_type=review_type,
            **validated_data
        )

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.services import notify
from .models import Review
from .serializers import ReviewSerializer


class CreateReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                review = serializer.save()
        except IntegrityError:
            return Response(
                {"success": False, "message": "Review could not be saved due to a database conflict."},
                status=status.HTTP_409_CONFLICT,
            )

        app = review.application
        if review.review_type == Review.ReviewType.APPLICANT_TO_POSTER:
            recipient = app.job.posted_by
        else:
            recipient = app.applicant
        notify(
            recipient,
            Notification.NotificationType.GENERAL,
            "New Review",
            f"You received a {review.rating}-star review for '{app.job.job_title}'.",
            job=app.job,
            application=app,
        )

        return Response(
            {"success": True, "message": "Review submitted successfully.", "data": ReviewSerializer(review).data},
            status=status.HTTP_201_CREATED,
        )


class ReviewListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reviews = Review.objects.filter(
            Q(application__applicant=request.user) | Q(application__job__posted_by=request.user)
        ).select_related("application", "reviewer").order_by("-created_at")

        return Response({"success": True, "count": reviews.count(), "data": ReviewSerializer(reviews, many=True).data})


class ReviewDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        review_id = request.data.get("review_id")
        review = Review.objects.filter(
            Q(application__applicant=request.user) | Q(application__job__posted_by=request.user),
            pk=review_id,
        ).select_related("application", "reviewer").first()

        if not review:
            return Response({"success": False, "message": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"success": True, "data": ReviewSerializer(review).data})


class UserRatingSummaryAPIView(APIView):
    """Average rating and review count for a user (received reviews only)."""
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"success": False, "message": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        as_applicant = Review.objects.filter(
            application__applicant_id=user_id,
            review_type=Review.ReviewType.POSTER_TO_APPLICANT,
        )
        as_poster = Review.objects.filter(
            application__job__posted_by_id=user_id,
            review_type=Review.ReviewType.APPLICANT_TO_POSTER,
        )
        all_received = as_applicant | as_poster
        stats = all_received.aggregate(avg=Avg("rating"), count=Count("id"))

        return Response({
            "success": True,
            "data": {
                "user_id": user_id,
                "average_rating": round(stats["avg"], 2) if stats["avg"] else None,
                "total_reviews": stats["count"],
            },
        })
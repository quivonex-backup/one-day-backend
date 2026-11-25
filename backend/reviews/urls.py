from django.urls import path
from .views import (
    CreateReviewAPIView,
    ReviewDetailAPIView,
    ReviewListAPIView,
    UserRatingSummaryAPIView,
)

urlpatterns = [
    path("create/", CreateReviewAPIView.as_view(), name="create-review"),
    path("my/", ReviewListAPIView.as_view(), name="review-list"),
    path("detail/", ReviewDetailAPIView.as_view(), name="review-detail"),
    path("user-rating/", UserRatingSummaryAPIView.as_view(), name="user-rating"),
]
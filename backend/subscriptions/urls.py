from django.urls import path

from .views import (
    ActivateFreePlanAPIView,
    AdminActivateSubscriptionAPIView,
    AdminApproveBulkHiringAPIView,
    AdminBulkHiringDetailAPIView,
    AdminBulkHiringListAPIView,
    AdminCancelSubscriptionAPIView,
    AdminCreatePlanAPIView,
    AdminPlanListAPIView,
    AdminRejectBulkHiringAPIView,
    AdminSetPlanActiveAPIView,
    AdminSubscriptionListAPIView,
    AdminUpdatePlanAPIView,
    CreatePaymentOrderAPIView,
    MyBulkHiringRequestsAPIView,
    MySubscriptionsAPIView,
    PlanDetailAPIView,
    PlanListAPIView,
    RazorpayWebhookAPIView,
    SubmitBulkHiringRequestAPIView,
    VerifyPaymentAPIView,
    MyPaymentOrdersAPIView,
    RetryPaymentAPIView,
)

urlpatterns = [
    # Users
    path("plans/", PlanListAPIView.as_view()),
    path("plans/detail/", PlanDetailAPIView.as_view()),
    path("my/", MySubscriptionsAPIView.as_view()),
    path("activate-free/", ActivateFreePlanAPIView.as_view()),

    # Razorpay payment
    path("payment/create-order/", CreatePaymentOrderAPIView.as_view()),
    path("payment/verify/", VerifyPaymentAPIView.as_view()),
    path("payment/razorpay/webhook/", RazorpayWebhookAPIView.as_view()),
    path("payment/retry/", RetryPaymentAPIView.as_view()),
    path("payment/my-orders/", MyPaymentOrdersAPIView.as_view()),

    # Bulk hiring: user
    path("bulk-hiring/request/", SubmitBulkHiringRequestAPIView.as_view()),
    path("bulk-hiring/my-requests/", MyBulkHiringRequestsAPIView.as_view()),

    # Admin: plans
    path("admin/plans/", AdminPlanListAPIView.as_view()),
    path("admin/plans/create/", AdminCreatePlanAPIView.as_view()),
    path("admin/plans/update/", AdminUpdatePlanAPIView.as_view()),
    path("admin/plans/set-active/", AdminSetPlanActiveAPIView.as_view()),

    # Admin: user subscriptions
    path("admin/subscriptions/", AdminSubscriptionListAPIView.as_view()),
    path("admin/subscriptions/activate/", AdminActivateSubscriptionAPIView.as_view()),
    path("admin/subscriptions/cancel/", AdminCancelSubscriptionAPIView.as_view()),

    # Admin: bulk hiring
    path("admin/bulk-hiring/", AdminBulkHiringListAPIView.as_view()),
    path("admin/bulk-hiring/detail/", AdminBulkHiringDetailAPIView.as_view()),
    path("admin/bulk-hiring/approve/", AdminApproveBulkHiringAPIView.as_view()),
    path("admin/bulk-hiring/reject/", AdminRejectBulkHiringAPIView.as_view()),
]
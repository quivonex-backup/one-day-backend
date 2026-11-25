from django.urls import path
from .views import *

urlpatterns = [
# Authenticated user job management
path("create/", CreateJobAPIView.as_view()),
path("list/", JobListAPIView.as_view()),
path("detail/", JobDetailAPIView.as_view()),
path("update/", UpdateJobAPIView.as_view()),
path("delete/", DeleteJobAPIView.as_view()),
path("hard-delete/", HardDeleteJobAPIView.as_view()),

path("my-jobs/", MyJobsAPIView.as_view()),
path("draft-jobs/", DraftJobsAPIView.as_view()),
path("payment-pending/", PaymentPendingJobsAPIView.as_view()),
path("pending-approval/", PendingApprovalJobsAPIView.as_view()),
path("published/", PublishedJobsAPIView.as_view()),
path("rejected/", RejectedJobsAPIView.as_view()),
path("close/", CloseJobAPIView.as_view()),
path("cancel/", CancelJobAPIView.as_view()),
path("closed/", ClosedJobsAPIView.as_view()),

path("recommended/", RecommendedJobsAPIView.as_view(), name="recommended-jobs",),

# Administrator moderation
path("admin/pending/", PendingJobsAPIView.as_view()),
path("admin/approve/", ApproveJobAPIView.as_view()),
path("admin/reject/", RejectJobAPIView.as_view()),
path("admin/published/", PublishedJobsAdminAPIView.as_view()),
path("admin/feature/", FeatureJobAPIView.as_view()),
path("admin/urgent/", UrgentJobAPIView.as_view()),

# Public job discovery
path("search/", SearchJobsAPIView.as_view()),
path("featured/", FeaturedJobsAPIView.as_view()),
path("urgent/", UrgentJobsAPIView.as_view()),
path("filter/", FilterJobsAPIView.as_view()),
path("public-detail/", PublicJobDetailAPIView.as_view()),
path("find/", FindJobsAPIView.as_view()),
path("nearby/", NearbyJobsAPIView.as_view()),



]

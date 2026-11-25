import math

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import is_admin
from applications.models import JobApplication
from subscriptions.services import consume_job_credit, posting_summary
from .models import Job
from .serializers import JobSerializer


def user_jobs(user, **filters):
    return Job.objects.filter(posted_by=user, **filters)

def annotate_applied_count(qs):
    return qs.annotate(
        applied_count=Count(
            "applications",
            filter=Q(applications__is_active=True),
        )
    )


def job_id_from_request(request):
    return request.data.get("id") or request.data.get("job_id")

# Job status rules
# - Owner can edit or cancel a job until it is closed, cancelled or completed.
# - Only a published job can be closed.
# - Admin can approve or reject only a job that is waiting for approval.
EDITABLE_STATUSES = {
    Job.Status.DRAFT,
    Job.Status.PAYMENT_PENDING,
    Job.Status.PENDING_APPROVAL,
    Job.Status.PUBLISHED,
    Job.Status.REJECTED,
}
CANCELLABLE_STATUSES = EDITABLE_STATUSES


def status_error(message, job):
    return Response(
        {"success": False, "message": message, "current_status": job.status},
        status=status.HTTP_400_BAD_REQUEST,
    )


def filter_jobs_by_location(jobs, data):
    """Filter jobs by the location fields stored from PostalLocation."""
    postal_location_id = data.get("postal_location_id")
    pincode = str(data.get("pincode") or "").strip()
    district = str(data.get("district") or "").strip()
    state = str(data.get("state") or "").strip()

    if postal_location_id:
        jobs = jobs.filter(postal_location_id=postal_location_id)
    if pincode:
        jobs = jobs.filter(pincode=pincode)
    if district:
        jobs = jobs.filter(district_name__iexact=district)
    if state:
        jobs = jobs.filter(state_name__iexact=state)

    return jobs


class CreateJobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        summary = posting_summary(request.user)
        if not summary["can_post_job"]:
            return Response(
                {"success": False, "message": "You need an active subscription to post jobs. Please buy a plan first."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vacancies = int(request.data.get("number_of_vacancies", 1) or 1)
        if vacancies > summary["max_vacancies_per_job"]:
            return Response(
                {
                    "success": False,
                    "message": f"Your plan allows up to {summary['max_vacancies_per_job']} vacancies per job.",
                    "max_vacancies_per_job": summary["max_vacancies_per_job"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = JobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            charged = consume_job_credit(request.user)
            if not charged:
                return Response(
                    {"success": False, "message": "No job credits remaining. Please upgrade your subscription."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            job = serializer.save(posted_by=request.user, status=Job.Status.PENDING_APPROVAL)

        return Response(
            {"success": True, "message": "Job created and sent for admin approval.", "data": JobSerializer(job).data},
            status=status.HTTP_201_CREATED,
        )


class JobListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        jobs = annotate_applied_count(user_jobs(request.user, is_active=True)).order_by("-created_at")
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})


class MyJobsAPIView(JobListAPIView):
    pass


class OwnedJobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_owned_job(self, request, include_inactive=False):
        job_id = job_id_from_request(request)
        if not job_id:
            return None, Response({"success": False, "message": "Job ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        filters = {"id": job_id, "posted_by": request.user}
        if not include_inactive:
            filters["is_active"] = True
        job = Job.objects.filter(**filters).first()
        if not job:
            return None, Response({"success": False, "message": "Job not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        return job, None


class JobDetailAPIView(OwnedJobAPIView):
    def post(self, request):
        job, error = self.get_owned_job(request)
        return error or Response({"success": True, "data": JobSerializer(job).data})


class UpdateJobAPIView(OwnedJobAPIView):
    def post(self, request):
        job, error = self.get_owned_job(request)
        if error:
            return error
        if job.status not in EDITABLE_STATUSES:
            return status_error(f"A {job.get_status_display().lower()} job cannot be edited.", job)
        serializer = JobSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Every edit goes back to the admin. Old approval/rejection is cleared.
        job = serializer.save(
            status=Job.Status.PENDING_APPROVAL,
            approved_by=None,
            approved_at=None,
            rejected_by=None,
            rejected_at=None,
            rejection_reason="",
        )
        return Response({"success": True, "message": "Job updated and sent for approval.", "data": JobSerializer(job).data})
    
    

class DeleteJobAPIView(OwnedJobAPIView):
    def post(self, request):
        job, error = self.get_owned_job(request)
        if error:
            return error
        job.is_active = False
        job.save(update_fields=["is_active", "updated_at"])
        return Response({"success": True, "message": "Job deleted successfully."})


class HardDeleteJobAPIView(OwnedJobAPIView):
    def post(self, request):
        job, error = self.get_owned_job(request, include_inactive=True)
        if error:
            return error
        # Permanent delete would also erase every application for this job.
        if job.applications.exists():
            return Response(
                {
                    "success": False,
                    "message": "This job has applications and cannot be permanently deleted. Close or cancel it instead.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.delete()
        return Response({"success": True, "message": "Job permanently deleted."})
    

class UserJobStatusListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    job_status = None

    def post(self, request):
        jobs = annotate_applied_count(user_jobs(request.user, status=self.job_status, is_active=True)).order_by("-created_at")
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})


class DraftJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.DRAFT


class PaymentPendingJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.PAYMENT_PENDING


class PendingApprovalJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.PENDING_APPROVAL


class PublishedJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.PUBLISHED


class RejectedJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.REJECTED


class ClosedJobsAPIView(UserJobStatusListAPIView):
    job_status = Job.Status.CLOSED


class CloseJobAPIView(OwnedJobAPIView):
    """Stop taking applications. Hired workers keep their jobs."""

    def post(self, request):
        job, error = self.get_owned_job(request)
        if error:
            return error
        if job.status != Job.Status.PUBLISHED:
            return status_error("Only published jobs can be closed.", job)
        job.status = Job.Status.CLOSED
        job.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "message": "Job closed successfully."})


class CancelJobAPIView(OwnedJobAPIView):
    """Cancel the job. Waiting applications are cancelled too."""

    def post(self, request):
        job, error = self.get_owned_job(request)
        if error:
            return error
        if job.status not in CANCELLABLE_STATUSES:
            return status_error(f"A {job.get_status_display().lower()} job cannot be cancelled.", job)
        if job.applications.filter(status=JobApplication.Status.HIRED, is_active=True).exists():
            return status_error(
                "This job has hired workers. Mark their work as completed or reject them before cancelling.",
                job,
            )
        with transaction.atomic():
            job.status = Job.Status.CANCELLED
            job.save(update_fields=["status", "updated_at"])
            job.applications.filter(
                status__in=[JobApplication.Status.APPLIED, JobApplication.Status.SHORTLISTED],
                is_active=True,
            ).update(status=JobApplication.Status.CANCELLED, updated_at=timezone.now())
        return Response({"success": True, "message": "Job cancelled successfully."})
    
    

class AdminJobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def deny_unless_admin(self, request):
        if not is_admin(request.user):
            return Response({"success": False, "message": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        return None


class PendingJobsAPIView(AdminJobAPIView):
    def post(self, request):
        error = self.deny_unless_admin(request)
        if error:
            return error
        jobs = annotate_applied_count(Job.objects.filter(status=Job.Status.PENDING_APPROVAL, is_active=True)).order_by("-created_at")
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})

def admin_get_job(request, lock=False):
    """Find an active job for an admin action. Returns (job, error_response)."""
    job_id = job_id_from_request(request)
    if not job_id:
        return None, Response({"success": False, "message": "Job ID is required."}, status=status.HTTP_400_BAD_REQUEST)
    jobs = Job.objects.select_for_update() if lock else Job.objects
    job = jobs.filter(id=job_id, is_active=True).first()
    if not job:
        return None, Response({"success": False, "message": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    return job, None


class ApproveJobAPIView(AdminJobAPIView):
    """PENDING_APPROVAL -> PUBLISHED"""

    def post(self, request):
        error = self.deny_unless_admin(request)
        if error:
            return error
        with transaction.atomic():
            job, error = admin_get_job(request, lock=True)
            if error:
                return error
            if job.status != Job.Status.PENDING_APPROVAL:
                return status_error("Only jobs waiting for approval can be approved.", job)
            if job.application_deadline < timezone.localdate():
                return status_error("The application deadline has passed. Ask the owner to update the dates.", job)

            job.status = Job.Status.PUBLISHED
            job.approved_by = request.user
            job.approved_at = timezone.now()
            job.rejected_by = None
            job.rejected_at = None
            job.rejection_reason = ""
            job.save(update_fields=[
                "status", "approved_by", "approved_at",
                "rejected_by", "rejected_at", "rejection_reason", "updated_at",
            ])
        return Response({"success": True, "message": "Job approved successfully."})


class RejectJobAPIView(AdminJobAPIView):
    """PENDING_APPROVAL -> REJECTED (reason is required)"""

    def post(self, request):
        error = self.deny_unless_admin(request)
        if error:
            return error
        reason = str(request.data.get("reason") or "").strip()
        if len(reason) < 5:
            return Response(
                {"success": False, "message": "Please give a rejection reason (at least 5 characters)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            job, error = admin_get_job(request, lock=True)
            if error:
                return error
            if job.status != Job.Status.PENDING_APPROVAL:
                return status_error("Only jobs waiting for approval can be rejected.", job)

            job.status = Job.Status.REJECTED
            job.rejected_by = request.user
            job.rejected_at = timezone.now()
            job.rejection_reason = reason[:1000]
            job.approved_by = None
            job.approved_at = None
            job.save(update_fields=[
                "status", "rejected_by", "rejected_at", "rejection_reason",
                "approved_by", "approved_at", "updated_at",
            ])
        return Response({"success": True, "message": "Job rejected successfully."})


class PublishedJobsAdminAPIView(AdminJobAPIView):
    def post(self, request):
        error = self.deny_unless_admin(request)
        if error:
            return error
        jobs = annotate_applied_count(Job.objects.filter(status=Job.Status.PUBLISHED, is_active=True)).order_by("-created_at")
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})


class AdminToggleJobAPIView(AdminJobAPIView):
    """Turn a flag on/off. Only for published jobs."""

    field = None
    message = "Job updated successfully."

    def post(self, request):
        error = self.deny_unless_admin(request)
        if error:
            return error
        job, error = admin_get_job(request)
        if error:
            return error
        if job.status != Job.Status.PUBLISHED:
            return status_error("Only published jobs can be featured or marked urgent.", job)
        setattr(job, self.field, not getattr(job, self.field))
        job.save(update_fields=[self.field, "updated_at"])
        return Response({"success": True, "message": self.message, self.field: getattr(job, self.field)})


class FeatureJobAPIView(AdminToggleJobAPIView):
    field, message = "is_featured", "Featured status updated successfully."


class UrgentJobAPIView(AdminToggleJobAPIView):
    field, message = "is_urgent", "Urgent status updated successfully."
    

class PublicJobsAPIView(APIView):
    permission_classes = [AllowAny]

    def queryset(self):
        return Job.objects.filter(status=Job.Status.PUBLISHED, is_active=True)


class FindJobsAPIView(PublicJobsAPIView):
    """
    One search API for the Find Jobs screen.
    All filters are optional and can be combined.
    """

    max_page_size = 50

    def post(self, request):
        data = request.data

        jobs = (
            self.queryset()
            .filter(application_deadline__gte=timezone.localdate())
            .select_related("postal_location", "job_category", "job_subcategory")
            .prefetch_related("skills", "languages")
        )

        # A logged-in user does not see their own jobs in Find Jobs.
        if request.user.is_authenticated:
            jobs = jobs.exclude(posted_by=request.user)

        # ==========================
        # Keyword
        # ==========================

        keyword = str(data.get("keyword") or "").strip()
        if keyword:
            jobs = jobs.filter(
                Q(job_title__icontains=keyword)
                | Q(job_description__icontains=keyword)
                | Q(job_category__name__icontains=keyword)
                | Q(job_subcategory__name__icontains=keyword)
            )

        # ==========================
        # Category / type filters
        # ==========================

        foreign_keys = {"job_category", "job_subcategory", "employment_type"}
        for field in ("job_category", "job_subcategory", "employment_type", "salary_type", "job_duration"):
            value = data.get(field)
            if value:
                jobs = jobs.filter(**{f"{field}_id" if field in foreign_keys else field: value})

        # ==========================
        # Location
        # ==========================

        location_data = data

        if str(data.get("use_profile_location", "")).lower() == "true":
            if not request.user.is_authenticated:
                return Response(
                    {"success": False, "message": "Login is required to use your profile location."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            profile = getattr(request.user, "profile", None)
            if not profile or not profile.city:
                return Response(
                    {"success": False, "message": "Please add your location in your profile first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Profile stores district in `city`.
            location_data = {"district": profile.city, "state": profile.state}

        pincode = str(location_data.get("pincode") or "").strip()
        if pincode and (len(pincode) != 6 or not pincode.isdigit()):
            return Response(
                {"success": False, "message": "Pincode must be exactly 6 digits."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jobs = filter_jobs_by_location(jobs, location_data)

        # ==========================
        # Ordering + pagination
        # ==========================

        jobs = jobs.order_by("-is_urgent", "-is_featured", "-created_at")

        try:
            page = max(int(data.get("page", 1)), 1)
            page_size = min(max(int(data.get("page_size", 20)), 1), self.max_page_size)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "page and page_size must be numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = jobs.count()
        start = (page - 1) * page_size
        page_jobs = jobs[start:start + page_size]

        return Response({
            "success": True,
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total else 0,
            "data": JobSerializer(page_jobs, many=True).data,
        })

class RecommendedJobsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    max_page_size = 50

    def post(self, request):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response(
                {
                    "success": True,
                    "message": "Complete your profile and add skills to receive job recommendations.",
                    "count": 0,
                    "data": [],
                }
            )

        skill_ids = list(
            profile.skills.values_list("id", flat=True)
        )

        if not skill_ids:
            return Response(
                {
                    "success": True,
                    "message": "Add skills to your profile to receive job recommendations.",
                    "count": 0,
                    "data": [],
                }
            )

        jobs = (
            Job.objects.filter(
                status=Job.Status.PUBLISHED,
                is_active=True,
                application_deadline__gte=timezone.localdate(),
                skills__in=skill_ids,
            )
            .exclude(posted_by=request.user)
            .select_related(
                "postal_location",
                "job_category",
                "job_subcategory",
            )
            .prefetch_related("skills", "languages")
            .annotate(
                matched_skill_count=Count(
                    "skills",
                    filter=Q(skills__in=skill_ids),
                    distinct=True,
                )
            )
            .order_by(
                "-matched_skill_count",
                "-is_urgent",
                "-is_featured",
                "-created_at",
            )
        )

        try:
            page = max(int(request.data.get("page", 1)), 1)
            page_size = min(
                max(int(request.data.get("page_size", 20)), 1),
                self.max_page_size,
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": "page and page_size must be numbers.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = jobs.count()
        start = (page - 1) * page_size
        page_jobs = jobs[start:start + page_size]

        return Response({
            "success": True,
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (
                math.ceil(total / page_size) if total else 0
            ),
            "data": JobSerializer(
                page_jobs,
                many=True,
            ).data,
        })

# Old URLs keep working and use the same search.
class SearchJobsAPIView(FindJobsAPIView):
    pass


class FilterJobsAPIView(FindJobsAPIView):
    pass


class NearbyJobsAPIView(FindJobsAPIView):
    pass


class FeaturedJobsAPIView(PublicJobsAPIView):
    def post(self, request):
        jobs = self.queryset().filter(is_featured=True)
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})


class UrgentJobsAPIView(PublicJobsAPIView):
    def post(self, request):
        jobs = self.queryset().filter(is_urgent=True)
        return Response({"success": True, "count": jobs.count(), "data": JobSerializer(jobs, many=True).data})


class PublicJobDetailAPIView(PublicJobsAPIView):
    def post(self, request):
        job = self.queryset().filter(id=job_id_from_request(request)).first()
        if not job:
            return Response({"success": False, "message": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "data": JobSerializer(job).data})
    
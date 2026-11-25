from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobApplication
from jobs.models import Job
from notifications.models import Notification
from notifications.services import notify
from .serializers import (
    ApplicantApplicationSerializer,
    JobApplicationSerializer,
    OwnerApplicationSerializer,
)

# Load related rows in one query instead of one per application.
OWNER_RELATED = ("job", "applicant", "applicant__profile")
APPLICANT_RELATED = ("job", "job__posted_by", "job__posted_by__profile")


class ApplyJobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = JobApplicationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            # The database unique rule (job + applicant) is the final guard
            # when two apply requests arrive at the same moment.
            with transaction.atomic():
                application = serializer.save()
        except IntegrityError:
            return Response(
                {"success": False, "message": "You have already applied for this job."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notify(
            application.job.posted_by,
            Notification.NotificationType.JOB_APPLICATION,
            "New Application",
            f"{request.user.email} applied for '{application.job.job_title}'.",
            job=application.job,
            application=application,
        )
        return Response(
            {"success": True, "message": "Job applied successfully.", "data": JobApplicationSerializer(application).data},
            status=status.HTTP_201_CREATED,
        )

class MyApplicationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        applications = (
            JobApplication.objects.filter(applicant=request.user, is_active=True)
            .select_related(*APPLICANT_RELATED)
            .order_by("-applied_at")
        )
        return Response({"success": True, "count": applications.count(), "data": ApplicantApplicationSerializer(applications, many=True).data})


class ApplicationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        application = JobApplication.objects.filter(
            id=request.data.get("application_id"),
            applicant=request.user,
            is_active=True,
        ).first()
        if not application:
            return Response({"success": False, "message": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "data": ApplicantApplicationSerializer(application).data})


class CancelApplicationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        application = JobApplication.objects.filter(pk=pk, applicant=request.user, is_active=True).first()
        if not application:
            return Response({"success": False, "message": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        if application.status != JobApplication.Status.APPLIED:
            return Response({"success": False, "message": "Only applied jobs can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        application.status = JobApplication.Status.CANCELLED
        application.save(update_fields=["status", "updated_at"])
        notify(
            application.job.posted_by,
            Notification.NotificationType.APPLICATION_CANCELLED,
            "Application Cancelled",
            f"{request.user.email} cancelled their application for '{application.job.job_title}'.",
            job=application.job,
            application=application,
        )
        return Response({"success": True, "message": "Application cancelled successfully."})


class OwnedJobApplicationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def owned_application(self, request, application_id):
        application = JobApplication.objects.filter(
            id=application_id,
            job__posted_by=request.user,
            job__is_active=True,
            is_active=True,
        ).first()
        if not application:
            return None, Response({"success": False, "message": "Application not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        return application, None


class JobApplicantsAPIView(OwnedJobApplicationsAPIView):
    def post(self, request):
        job_id = request.data.get("job_id")
        if not Job.objects.filter(id=job_id, posted_by=request.user).exists():
            return Response(
                {"success": False, "message": "Job not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )
        applications = (
            JobApplication.objects.filter(job_id=job_id, is_active=True)
            .select_related(*OWNER_RELATED)
            .prefetch_related("applicant__profile__skills")
            .order_by("-applied_at")
        )
        return Response({"success": True, "count": applications.count(), "data": OwnerApplicationSerializer(applications, many=True).data})
    

class ApplicantDetailAPIView(OwnedJobApplicationsAPIView):
    def post(self, request):
        application, error = self.owned_application(request, request.data.get("application_id"))
        return error or Response({"success": True, "data": OwnerApplicationSerializer(application).data})


def change_application_status(request, pk, allowed_statuses, new_status, success_message):
    with transaction.atomic():
        application = (
            JobApplication.objects.select_for_update()
            .filter(pk=pk, job__posted_by=request.user, job__is_active=True, is_active=True)
            .first()
        )
        if not application:
            return Response({"success": False, "message": "Application not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        if application.status not in allowed_statuses:
            return Response(
                {
                    "success": False,
                    "message": "Invalid application status transition.",
                    "current_status": application.status,
                    "allowed_statuses": allowed_statuses,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.status = new_status
        application.save(update_fields=["status", "updated_at"])

    STATUS_NOTIFICATION_MAP = {
        JobApplication.Status.SHORTLISTED: (Notification.NotificationType.SHORTLISTED, "Shortlisted"),
        JobApplication.Status.REJECTED: (Notification.NotificationType.REJECTED, "Application Rejected"),
        JobApplication.Status.HIRED: (Notification.NotificationType.HIRED, "You're Hired!"),
        JobApplication.Status.COMPLETED: (Notification.NotificationType.JOB_COMPLETED, "Job Completed"),
    }
    ntype, ntitle = STATUS_NOTIFICATION_MAP[new_status]
    notify(
        application.applicant,
        ntype,
        ntitle,
        f"Your application for '{application.job.job_title}' has been updated to {new_status}.",
        job=application.job,
        application=application,
    )
    return Response({"success": True, "message": success_message, "data": {"application_id": application.id, "status": application.status}})


class ShortlistApplicantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return change_application_status(request, pk, [JobApplication.Status.APPLIED], JobApplication.Status.SHORTLISTED, "Applicant shortlisted successfully.")


class RejectApplicantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return change_application_status(
            request, pk,
            [JobApplication.Status.APPLIED, JobApplication.Status.SHORTLISTED],
            JobApplication.Status.REJECTED,
            "Applicant rejected successfully.",
        )


class HireApplicantAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return change_application_status(request, pk, [JobApplication.Status.SHORTLISTED], JobApplication.Status.HIRED, "Applicant hired successfully.")


class CompleteJobAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return change_application_status(request, pk, [JobApplication.Status.HIRED], JobApplication.Status.COMPLETED, "Job application completed successfully.")

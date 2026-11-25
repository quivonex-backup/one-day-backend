from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import is_admin
from accounts.models import User
from applications.models import JobApplication
from jobs.models import Job


class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_admin(request.user):
            return Response(
                {
                    "success": False,
                    "message": "Admin access only.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "total_users": User.objects.filter(
                        is_staff=False,
                    ).count(),
                    "total_jobs": Job.objects.count(),
                    "published_jobs": Job.objects.filter(
                        status=Job.Status.PUBLISHED,
                        is_active=True,
                    ).count(),
                    "pending_jobs": Job.objects.filter(
                        status=Job.Status.PENDING_APPROVAL,
                        is_active=True,
                    ).count(),
                    "total_applications": JobApplication.objects.count(),
                    "hired_applications": JobApplication.objects.filter(
                        status=JobApplication.Status.HIRED,
                        is_active=True,
                    ).count(),
                },
            }
        )


class PostingDashboardAPIView(APIView):
    """Dashboard for the current user's job-posting activity."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        jobs = Job.objects.filter(posted_by=request.user)
        applications = JobApplication.objects.filter(
            job__posted_by=request.user,
            is_active=True,
        )

        return Response(
            {
                "success": True,
                "data": {
                    "total_jobs": jobs.count(),
                    "published_jobs": jobs.filter(
                        status=Job.Status.PUBLISHED,
                        is_active=True,
                    ).count(),
                    "pending_jobs": jobs.filter(
                        status=Job.Status.PENDING_APPROVAL,
                        is_active=True,
                    ).count(),
                    "total_applications": applications.count(),
                    "hired_applications": applications.filter(
                        status=JobApplication.Status.HIRED,
                    ).count(),
                },
            }
        )


class ApplicationDashboardAPIView(APIView):
    """Dashboard for the current user's job applications."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        applications = JobApplication.objects.filter(
            applicant=request.user,
            is_active=True,
        )

        return Response(
            {
                "success": True,
                "data": {
                    "total_applications": applications.count(),
                    "applied_applications": applications.filter(
                        status=JobApplication.Status.APPLIED,
                    ).count(),
                    "shortlisted_applications": applications.filter(
                        status=JobApplication.Status.SHORTLISTED,
                    ).count(),
                    "hired_applications": applications.filter(
                        status=JobApplication.Status.HIRED,
                    ).count(),
                    "completed_applications": applications.filter(
                        status=JobApplication.Status.COMPLETED,
                    ).count(),
                },
            }
        )
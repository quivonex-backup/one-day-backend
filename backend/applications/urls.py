from django.urls import path

from .views import (
    ApplyJobAPIView,
    MyApplicationsAPIView,
    ApplicationDetailAPIView,
    CancelApplicationAPIView,
    JobApplicantsAPIView,
    ApplicantDetailAPIView,
    ShortlistApplicantAPIView,
    RejectApplicantAPIView,
    HireApplicantAPIView,
    CompleteJobAPIView
)

urlpatterns = [

    # Employee
    path("apply/", ApplyJobAPIView.as_view(), name="apply-job"),
    path("my-applications/", MyApplicationsAPIView.as_view(), name="my-applications"),
    path("details/", ApplicationDetailAPIView.as_view(), name="application-details"),

    # FIX: Pass application ID to the cancel view
    path("cancel/<int:pk>/", CancelApplicationAPIView.as_view(), name="cancel-application"),

    # Employer
    path("applicants/", JobApplicantsAPIView.as_view(), name="job-applicants"),
    path("applicant-details/", ApplicantDetailAPIView.as_view(), name="applicant-details"),

    # FIX: Pass application ID to employer action views
    path("shortlist/<int:pk>/", ShortlistApplicantAPIView.as_view(), name="shortlist-applicant"),
    path("reject/<int:pk>/", RejectApplicantAPIView.as_view(), name="reject-applicant"),
    path("hire/<int:pk>/", HireApplicantAPIView.as_view(), name="hire-applicant"),
    path("complete/<int:pk>/",CompleteJobAPIView.as_view(),name="complete-job"),
    
    
]

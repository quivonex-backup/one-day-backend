from django.urls import path

from .views import (
    AdminDashboardAPIView,
    ApplicationDashboardAPIView,
    PostingDashboardAPIView,
)

urlpatterns = [
    path("admin/", AdminDashboardAPIView.as_view(), name="admin-dashboard"),
    path("posting/", PostingDashboardAPIView.as_view(), name="posting-dashboard", ),
    path("applications/", ApplicationDashboardAPIView.as_view(), name="applications-dashboard",),
]
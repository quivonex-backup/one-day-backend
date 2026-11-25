from django.urls import path

from .views import (
    MyNotificationsAPIView,
    UnreadNotificationCountAPIView,
    MarkNotificationReadAPIView,
    MarkAllNotificationsReadAPIView,
)

urlpatterns = [
    path("my/", MyNotificationsAPIView.as_view()),
    path("unread-count/", UnreadNotificationCountAPIView.as_view()),
    path("mark-read/", MarkNotificationReadAPIView.as_view()),
    path("mark-all-read/", MarkAllNotificationsReadAPIView.as_view()),
]
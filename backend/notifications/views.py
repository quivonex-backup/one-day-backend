from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notifications = Notification.objects.filter(user=request.user)
        ntype = request.data.get("type")
        if ntype:
            notifications = notifications.filter(notification_type=ntype)
        return Response({
            "success": True,
            "count": notifications.count(),
            "data": NotificationSerializer(notifications, many=True).data,
        })


class UnreadNotificationCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"success": True, "unread_count": count})


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notification_id = request.data.get("notification_id")
        if not notification_id:
            return Response(
                {"success": False, "message": "notification_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notification = Notification.objects.filter(id=notification_id, user=request.user).first()
        if not notification:
            return Response(
                {"success": False, "message": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return Response({"success": True, "message": "Notification marked as read."})


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({
            "success": True,
            "message": "All notifications marked as read.",
            "updated_count": updated,
        })

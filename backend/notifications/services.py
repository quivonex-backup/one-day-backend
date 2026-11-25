"""
Create notifications safely, after the current transaction commits.

Usage:
    from notifications.services import notify
    notify(user, Type.HIRED, "You're hired!", "...", job=job, application=app)
"""

from django.db import transaction

from .models import Notification


def notify(user, notification_type, title, message, *, job=None, application=None):
    """Queue a notification to be created after the current transaction commits."""
    def _create():
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            job=job,
            application=application,
        )

    transaction.on_commit(_create)

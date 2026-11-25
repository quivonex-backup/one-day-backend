"""Subscription rules used by views and job posting enforcement."""

from django.db.models import F
from django.utils import timezone

from .models import UserSubscription


def active_subscriptions(user):
    """Paid/active subscriptions that have not expired, soonest ending first."""
    return UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.Status.ACTIVE,
        ends_at__gt=timezone.now(),
    ).order_by("ends_at", "id")


def posting_summary(user):
    """What the user can post right now, across all active subscriptions."""
    usable = [s for s in active_subscriptions(user) if s.jobs_remaining > 0]
    return {
        "can_post_job": bool(usable),
        "jobs_remaining": sum(s.jobs_remaining for s in usable),
        "max_vacancies_per_job": max((s.max_vacancies_per_job for s in usable), default=0),
        "next_expiry": usable[0].ends_at if usable else None,
    }


def has_used_free_plan(user):
    return UserSubscription.objects.filter(
        user=user,
        source=UserSubscription.Source.FREE,
    ).exists()


def consume_job_credit(user):
    """
    Use one job credit from the soonest-expiring active subscription.

    Returns the subscription that was charged, or None if the user has
    no remaining credits. Uses F() + filter to avoid race conditions.
    """
    candidates = active_subscriptions(user)
    for sub in candidates:
        updated = UserSubscription.objects.filter(
            pk=sub.pk,
            jobs_used__lt=F("job_post_limit"),
        ).update(jobs_used=F("jobs_used") + 1)
        if updated:
            sub.refresh_from_db()
            return sub
    return None
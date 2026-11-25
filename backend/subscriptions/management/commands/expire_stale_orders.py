from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import PaymentOrder, UserSubscription


class Command(BaseCommand):
    help = "Mark CREATED payment orders older than 30 minutes as FAILED and cancel their PENDING_PAYMENT subscriptions."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=30, help="Age threshold in minutes (default 30).")
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without changing anything.")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=options["minutes"])

        stale_orders = PaymentOrder.objects.filter(
            status=PaymentOrder.Status.CREATED,
            created_at__lt=cutoff,
        ).select_related("subscription")

        count = stale_orders.count()
        if options["dry_run"]:
            self.stdout.write(f"[DRY RUN] {count} stale order(s) would be expired.")
            return

        expired = 0
        for order in stale_orders:
            order.status = PaymentOrder.Status.FAILED
            order.status_reason = "Expired: no payment received within retry window"
            order.save(update_fields=["status", "status_reason", "updated_at"])

            sub = order.subscription
            if sub.status == UserSubscription.Status.PENDING_PAYMENT:
                has_other_active_order = PaymentOrder.objects.filter(
                    subscription=sub,
                    status=PaymentOrder.Status.CREATED,
                ).exclude(pk=order.pk).exists()
                if not has_other_active_order:
                    sub.status = UserSubscription.Status.CANCELLED
                    sub.save(update_fields=["status", "updated_at"])

            expired += 1

        self.stdout.write(self.style.SUCCESS(f"{expired} stale order(s) expired."))
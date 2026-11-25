from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.models import JobApplication
from jobs.models import Job
from notifications.models import Notification
from notifications.services import notify


class Command(BaseCommand):
    help = "Close published jobs whose application deadline has passed."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be closed without changing anything.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        expired = Job.objects.filter(
            status=Job.Status.PUBLISHED,
            is_active=True,
            application_deadline__lt=today,
        )

        count = expired.count()
        if options["dry_run"]:
            self.stdout.write(f"[DRY RUN] {count} job(s) would be closed.")
            for job in expired[:20]:
                self.stdout.write(f"  - #{job.id} '{job.job_title}' (deadline {job.application_deadline})")
            return

        closed = 0
        for job in expired.select_related("posted_by"):
            job.status = Job.Status.CLOSED
            job.save(update_fields=["status", "updated_at"])

            JobApplication.objects.filter(
                job=job,
                status=JobApplication.Status.APPLIED,
                is_active=True,
            ).update(status=JobApplication.Status.CANCELLED, updated_at=timezone.now())

            notify(
                job.posted_by,
                Notification.NotificationType.GENERAL,
                "Job Auto-Closed",
                f"Your job '{job.job_title}' has been automatically closed because the application deadline passed.",
                job=job,
            )
            closed += 1

        self.stdout.write(self.style.SUCCESS(f"{closed} job(s) closed."))
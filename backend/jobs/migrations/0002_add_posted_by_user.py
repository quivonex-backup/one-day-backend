from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_job_owners(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    for job in Job.objects.filter(posted_by__isnull=True, employer__isnull=False).select_related("employer"):
        job.posted_by_id = job.employer.user_id
        job.save(update_fields=["posted_by"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_backfill_activity_flags"),
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="posted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posted_jobs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="employer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="legacy_jobs",
                to="employers.employer",
            ),
        ),
        migrations.RunPython(copy_legacy_job_owners, migrations.RunPython.noop),
    ]

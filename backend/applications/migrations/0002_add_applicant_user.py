from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_applicants(apps, schema_editor):
    JobApplication = apps.get_model("applications", "JobApplication")
    for application in JobApplication.objects.filter(applicant__isnull=True, employee__isnull=False).select_related("employee"):
        application.applicant_id = application.employee.user_id
        application.save(update_fields=["applicant"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_backfill_activity_flags"),
        ("applications", "0001_initial"),
        ("jobs", "0002_add_posted_by_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="applicant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="job_applications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="jobapplication",
            name="employee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="legacy_applications",
                to="employees.employee",
            ),
        ),
        migrations.RunPython(copy_legacy_applicants, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="jobapplication",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="jobapplication",
            constraint=models.UniqueConstraint(fields=("job", "applicant"), name="unique_active_job_applicant"),
        ),
    ]

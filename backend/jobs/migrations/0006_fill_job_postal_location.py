from django.db import migrations


def fill_postal_location(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    PostalLocation = apps.get_model("common", "PostalLocation")

    for job in Job.objects.filter(postal_location__isnull=True):
        location = (
            PostalLocation.objects
            .filter(pincode=job.pincode)
            .order_by("post_office")
            .first()
        )

        # No postal record for this pincode: leave the job as it is.
        if location is None:
            continue

        job.postal_location = location
        job.pincode = location.pincode
        job.district_name = location.district_name
        job.state_name = location.state_name
        job.save(update_fields=[
            "postal_location",
            "pincode",
            "district_name",
            "state_name",
        ])


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0005_postallocation"),
        ("jobs", "0005_remove_job_jobs_state_i_f3ee90_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_postal_location, migrations.RunPython.noop),
    ]
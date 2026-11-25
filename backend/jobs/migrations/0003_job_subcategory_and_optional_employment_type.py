from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0003_jobsubcategory"),
        ("jobs", "0002_add_posted_by_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="job_subcategory",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="jobs",
                to="common.jobsubcategory",
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="employment_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="jobs",
                to="common.employmenttype",
            ),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["job_subcategory"], name="jobs_job_sub_97c721_idx"),
        ),
    ]

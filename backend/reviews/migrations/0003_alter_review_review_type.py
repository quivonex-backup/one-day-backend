from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0002_review_review_rating_between_1_and_5"),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="review_type",
            field=models.CharField(
                choices=[
                    ("EMPLOYEE_TO_EMPLOYER", "Applicant to job poster"),
                    ("EMPLOYER_TO_EMPLOYEE", "Job poster to applicant"),
                ],
                max_length=30,
            ),
        ),
    ]

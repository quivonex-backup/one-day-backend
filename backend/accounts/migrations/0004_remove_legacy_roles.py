from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_backfill_activity_flags"),
        ("applications", "0002_add_applicant_user"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="role"),
        migrations.RemoveField(model_name="user", name="is_employee"),
        migrations.RemoveField(model_name="user", name="is_employer"),
    ]

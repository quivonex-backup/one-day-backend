from django.db import migrations
from django.db.models import Q


def backfill_activity_flags(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Employee = apps.get_model("employees", "Employee")
    Employer = apps.get_model("employers", "Employer")
    alias = schema_editor.connection.alias
    users = User.objects.using(alias).filter(is_staff=False, is_superuser=False).exclude(role="ADMIN")
    users.filter(
        Q(role="EMPLOYEE") | Q(pk__in=Employee.objects.using(alias).values("user_id"))
    ).update(is_employee=True)
    users.filter(
        Q(role="EMPLOYER") | Q(pk__in=Employer.objects.using(alias).values("user_id"))
    ).update(is_employer=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_loginotpchallenge_user_is_employee_user_is_employer_and_more"),
        ("employees", "0004_alter_employee_education_level_and_more"),
        ("employers", "0002_employer_rejected_at_employer_rejected_by_and_more"),
    ]
    # Do not remove capabilities if this data migration is rolled back.
    operations = [migrations.RunPython(backfill_activity_flags, migrations.RunPython.noop)]

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from common.models import PostalLocation


class Command(BaseCommand):
    help = (
        "Import India PIN directory CSV into common.PostalLocation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Path of the downloaded India PIN CSV file.",
        )

    @staticmethod
    def normalize_key(value: str) -> str:
        return "".join(
            character
            for character in value.lower()
            if character.isalnum()
        )

    @classmethod
    def row_value(cls, row: dict, *possible_names: str) -> str:
        for name in possible_names:
            value = row.get(cls.normalize_key(name), "").strip()

            if value:
                return value

        return ""

    def handle(self, *args, **options):
        csv_path = Path(options["file"]).expanduser()

        if not csv_path.is_file():
            raise CommandError(
                f"CSV file not found: {csv_path}"
            )

        created_rows = []
        imported = 0
        skipped = 0
        batch_size = 1000

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                raise CommandError(
                    "The CSV file does not contain headers."
                )

            for raw_row in reader:
                row = {
                    self.normalize_key(key): str(value or "").strip()
                    for key, value in raw_row.items()
                    if key
                }

                pincode = self.row_value(
                    row,
                    "pincode",
                    "pin code",
                    "pin_code",
                )

                post_office = self.row_value(
                    row,
                    "officename",
                    "office name",
                    "post office",
                    "postoffice",
                )

                district_name = self.row_value(
                    row,
                    "district",
                    "districtname",
                    "district name",
                )

                state_name = self.row_value(
                    row,
                    "state",
                    "statename",
                    "state name",
                )

                office_type = self.row_value(
                    row,
                    "officetype",
                    "office type",
                )

                delivery_status = self.row_value(
                    row,
                    "delivery",
                    "delivery status",
                    "delivery status office",
                )

                if (
                    not pincode.isdigit()
                    or len(pincode) != 6
                    or not post_office
                    or not district_name
                    or not state_name
                ):
                    skipped += 1
                    continue

                created_rows.append(
                    PostalLocation(
                        pincode=pincode,
                        post_office=post_office,
                        district_name=district_name,
                        state_name=state_name,
                        office_type=office_type,
                        delivery_status=delivery_status,
                        is_active=True,
                    )
                )

                if len(created_rows) >= batch_size:
                    PostalLocation.objects.bulk_create(
                        created_rows,
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )
                    imported += len(created_rows)
                    created_rows = []

        if created_rows:
            PostalLocation.objects.bulk_create(
                created_rows,
                batch_size=batch_size,
                ignore_conflicts=True,
            )
            imported += len(created_rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import finished. Processed: {imported}. "
                f"Skipped invalid rows: {skipped}."
            )
        )
        
from django.db import models


class BaseMasterModel(models.Model):
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class State(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    state_code = models.CharField(max_length=10, unique=True)

    class Meta:
        db_table = "states"
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(BaseMasterModel):

    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="districts")

    name = models.CharField(max_length=100)

    district_code = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = "districts"
        ordering = ["name"]
        unique_together = ("state", "name")

    def __str__(self):
        return self.name


class Taluka(BaseMasterModel):

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="talukas")

    name = models.CharField(max_length=100)

    taluka_code = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = "talukas"
        ordering = ["name"]
        unique_together = ("district", "name")

    def __str__(self):
        return self.name


class Location(BaseMasterModel):

    taluka = models.ForeignKey(Taluka, on_delete=models.CASCADE, related_name="locations")

    name = models.CharField(max_length=150)

    pincode = models.CharField(max_length=6, blank=True, null=True, db_index=True,)

    class Meta:
        db_table = "locations"
        ordering = ["name"]
        unique_together = ("taluka", "name")

    def __str__(self):
        return self.name


class Skill(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "skills"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Language(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "languages"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobCategory(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    # icon = models.ImageField(upload_to="job_categories/", blank=True, null=True)

    class Meta:
        db_table = "job_categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobType(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    class Meta:
        db_table = "job_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EducationLevel(BaseMasterModel):

    name = models.CharField(max_length=100,unique=True)

    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "education_levels"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class ExperienceLevel(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    min_year = models.PositiveIntegerField(default=0)

    max_year = models.PositiveIntegerField(blank=True, null=True)

    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "experience_levels"
        ordering = ["display_order"]

    def __str__(self):
        return self.name


class EmploymentType(BaseMasterModel):

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "employment_types"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    
#########################

class JobSubCategory(BaseMasterModel):

    # Link subcategory to Tech or Non-Tech category
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.PROTECT,
        related_name="subcategories"
    )

    name = models.CharField(max_length=150)

    class Meta:
        db_table = "job_subcategories"
        ordering = ["name"]

        # Prevent duplicate subcategories under one category
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_job_subcategory_per_category"
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.name}"



class PostalLocation(BaseMasterModel):
    """
    Official PIN directory record.

    This is separate from Location because postal data provides
    State, District and Post Office/Village, but not a reliable Taluka.
    """

    pincode = models.CharField(
        max_length=6,
        db_index=True,
    )

    post_office = models.CharField(
        max_length=200,
    )

    district_name = models.CharField(
        max_length=150,
    )

    state_name = models.CharField(
        max_length=150,
    )

    office_type = models.CharField(
        max_length=50,
        blank=True,
    )

    delivery_status = models.CharField(
        max_length=100,
        blank=True,
    )

    class Meta:
        db_table = "postal_locations"
        ordering = ["pincode", "post_office"]

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "pincode",
                    "post_office",
                    "district_name",
                    "state_name",
                ),
                name="unique_postal_location",
            )
        ]

    def __str__(self):
        return f"{self.pincode} - {self.post_office}"
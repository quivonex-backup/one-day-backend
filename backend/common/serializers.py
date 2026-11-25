from rest_framework import serializers

from .models import (
    State,
    District,
    Taluka,
    Location,
    PostalLocation,
    Skill,
    Language,
    JobCategory,
    JobSubCategory,
    JobType,
    EducationLevel,
    ExperienceLevel,
    EmploymentType,
)


class StateSerializer(serializers.ModelSerializer):

    class Meta:
        model = State
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):

    state_name = serializers.CharField(
        source="state.name",
        read_only=True
    )

    class Meta:
        model = District
        fields = "__all__"


class TalukaSerializer(serializers.ModelSerializer):

    district_name = serializers.CharField(
        source="district.name",
        read_only=True
    )

    class Meta:
        model = Taluka
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):

    taluka_name = serializers.CharField(
        source="taluka.name",
        read_only=True
    )

    class Meta:
        model = Location
        fields = "__all__"


class PincodePostalLocationSerializer(serializers.ModelSerializer):

    class Meta:
        model = PostalLocation

        fields = (
            "id",
            "pincode",
            "post_office",
            "district_name",
            "state_name",
            "office_type",
            "delivery_status",
        )
        

class SkillSerializer(serializers.ModelSerializer):

    class Meta:
        model = Skill
        fields = "__all__"


class LanguageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Language
        fields = "__all__"


class JobCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = JobCategory
        fields = "__all__"


class JobTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobType
        fields = "__all__"


class EducationLevelSerializer(serializers.ModelSerializer):

    class Meta:
        model = EducationLevel
        fields = "__all__"


class ExperienceLevelSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExperienceLevel
        fields = "__all__"


class EmploymentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmploymentType
        fields = "__all__"
        
        
        
class JobSubCategorySerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = JobSubCategory
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_active", "created_at", "updated_at")
        # Duplicate check is done in validate() (case-insensitive).
        validators = []

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected job category is not active.")
        return value

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Subcategory name must contain at least 2 characters.")
        return value

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        name = attrs.get("name", getattr(self.instance, "name", None))

        duplicates = JobSubCategory.objects.filter(category=category, name__iexact=name)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise serializers.ValidationError({
                "name": "This subcategory already exists in the selected category."
            })

        return attrs
    
    


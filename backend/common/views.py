from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import IsAdmin
from .models import (
    State, District, Taluka, Location, Skill, Language, JobCategory, JobSubCategory, JobType, EducationLevel, ExperienceLevel, EmploymentType, PostalLocation,)

from .serializers import (StateSerializer, PincodePostalLocationSerializer, DistrictSerializer, TalukaSerializer, LocationSerializer, SkillSerializer, LanguageSerializer, JobCategorySerializer, JobSubCategorySerializer, JobTypeSerializer, EducationLevelSerializer, ExperienceLevelSerializer, EmploymentTypeSerializer,)


class CreateStateAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        serializer = StateSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "State created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
class StateListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        queryset = State.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = StateSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": "State list fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
        
class StateDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        state = State.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not state:

            return Response(
                {
                    "success": False,
                    "message": "State not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StateSerializer(state)

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
        
        
class UpdateStateAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        state = State.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not state:

            return Response(
                {
                    "success": False,
                    "message": "State not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StateSerializer(
            state,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "State updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
class DeleteStateAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        state = State.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not state:

            return Response(
                {
                    "success": False,
                    "message": "State not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        state.delete()
        return Response(
            {
                "success": True,
                "message": "State deleted successfully."
            },
            status=status.HTTP_200_OK
        )
        
        
class CreateDistrictAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        serializer = DistrictSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "District created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
class DistrictListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        queryset = District.objects.filter(
            is_active=True
        ).order_by("name")

        state_id = request.data.get("state_id")

        if state_id:
            queryset = queryset.filter(state_id=state_id)

        serializer = DistrictSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": "District list fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
        
class DistrictDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        district = District.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not district:

            return Response(
                {
                    "success": False,
                    "message": "District not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DistrictSerializer(district)

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
        
class UpdateDistrictAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        district = District.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not district:

            return Response(
                {
                    "success": False,
                    "message": "District not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DistrictSerializer(
            district,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "District updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
        
class DeleteDistrictAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        district = District.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not district:

            return Response(
                {
                    "success": False,
                    "message": "District not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        district.delete()

        return Response(
            {
                "success": True,
                "message": "District deleted successfully."
            },
            status=status.HTTP_200_OK
        )
        
class CreateTalukaAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        serializer = TalukaSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Taluka created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
        
class TalukaListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        queryset = Taluka.objects.filter(
            is_active=True
        ).order_by("name")

        district_id = request.data.get("district_id")

        if district_id:
            queryset = queryset.filter(
                district_id=district_id
            )

        serializer = TalukaSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": "Taluka list fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
        
class TalukaDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        taluka = Taluka.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not taluka:

            return Response(
                {
                    "success": False,
                    "message": "Taluka not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TalukaSerializer(taluka)

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
        
class UpdateTalukaAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        taluka = Taluka.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not taluka:

            return Response(
                {
                    "success": False,
                    "message": "Taluka not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TalukaSerializer(
            taluka,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Taluka updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
class DeleteTalukaAPIView(APIView):

    permission_classes = [IsAdmin]

    def post(self, request):

        taluka = Taluka.objects.filter(
            id=request.data.get("id"),
            is_active=True
        ).first()

        if not taluka:

            return Response(
                {
                    "success": False,
                    "message": "Taluka not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        taluka.delete()

        return Response(
            {
                "success": True,
                "message": "Taluka deleted successfully."
            },
            status=status.HTTP_200_OK
        )
        
from common.base_views import BaseMasterAPIView

class CreateLocationAPIView(BaseMasterAPIView):

    model = Location
    serializer_class = LocationSerializer
    model_name = "Location"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Location created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)
    
class LocationListAPIView(BaseMasterAPIView):

    model = Location
    serializer_class = LocationSerializer
    model_name = "Location"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        taluka_id = request.data.get("taluka_id")

        if taluka_id:
            queryset = queryset.filter(
                taluka_id=taluka_id
            )

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Location list fetched successfully.",
            serializer.data
        )
        
        
class LocationDetailAPIView(BaseMasterAPIView):

    model = Location
    serializer_class = LocationSerializer
    model_name = "Location"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Location not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Location fetched successfully.",
            serializer.data
        )
        
        
class UpdateLocationAPIView(BaseMasterAPIView):

    model = Location
    serializer_class = LocationSerializer
    model_name = "Location"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Location not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Location updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )
        
        
class DeleteLocationAPIView(BaseMasterAPIView):

    model = Location
    serializer_class = LocationSerializer
    model_name = "Location"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Location not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Location deleted successfully."
        )
        
        
class CreateSkillAPIView(BaseMasterAPIView):

    model = Skill
    serializer_class = SkillSerializer
    model_name = "Skill"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Skill created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)
    
class SkillListAPIView(BaseMasterAPIView):

    model = Skill
    serializer_class = SkillSerializer
    model_name = "Skill"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Skill list fetched successfully.",
            serializer.data
        )
        
        
class SkillDetailAPIView(BaseMasterAPIView):

    model = Skill
    serializer_class = SkillSerializer
    model_name = "Skill"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Skill not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Skill fetched successfully.",
            serializer.data
        )
        
class UpdateSkillAPIView(BaseMasterAPIView):

    model = Skill
    serializer_class = SkillSerializer
    model_name = "Skill"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Skill not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Skill updated successfully.",
                serializer.data
            )

        return self.validation_error(serializer.errors)
    
class DeleteSkillAPIView(BaseMasterAPIView):

    model = Skill
    serializer_class = SkillSerializer
    model_name = "Skill"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Skill not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Skill deleted successfully."
        )
        
class CreateLanguageAPIView(BaseMasterAPIView):

    model = Language
    serializer_class = LanguageSerializer
    model_name = "Language"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Language created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)
    
    
class LanguageListAPIView(BaseMasterAPIView):

    model = Language
    serializer_class = LanguageSerializer
    model_name = "Language"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Language list fetched successfully.",
            serializer.data
        )
        
        
class LanguageDetailAPIView(BaseMasterAPIView):

    model = Language
    serializer_class = LanguageSerializer
    model_name = "Language"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Language not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Language fetched successfully.",
            serializer.data
        )
        
        
class UpdateLanguageAPIView(BaseMasterAPIView):

    model = Language
    serializer_class = LanguageSerializer
    model_name = "Language"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Language not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Language updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )
        
        
class DeleteLanguageAPIView(BaseMasterAPIView):

    model = Language
    serializer_class = LanguageSerializer
    model_name = "Language"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Language not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Language deleted successfully."
        )
        
        
class CreateJobCategoryAPIView(BaseMasterAPIView):

    model = JobCategory
    serializer_class = JobCategorySerializer
    model_name = "Job Category"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job category created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)
    
    
class JobCategoryListAPIView(BaseMasterAPIView):

    model = JobCategory
    serializer_class = JobCategorySerializer
    model_name = "Job Category"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Job category list fetched successfully.",
            serializer.data
        )
        
        
class JobCategoryDetailAPIView(BaseMasterAPIView):

    model = JobCategory
    serializer_class = JobCategorySerializer
    model_name = "Job Category"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job category not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Job category fetched successfully.",
            serializer.data
        )
        
        
class UpdateJobCategoryAPIView(BaseMasterAPIView):

    model = JobCategory
    serializer_class = JobCategorySerializer
    model_name = "Job Category"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job category not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job category updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )
        
        
class DeleteJobCategoryAPIView(BaseMasterAPIView):

    model = JobCategory
    serializer_class = JobCategorySerializer
    model_name = "Job Category"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job category not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Job category deleted successfully."
        )
        
        
        
# ==========================================
# JOB SUBCATEGORY CRUD APIs
# ==========================================

class CreateJobSubCategoryAPIView(BaseMasterAPIView):

    permission_classes = [IsAdmin]
    model = JobSubCategory
    serializer_class = JobSubCategorySerializer
    model_name = "Job Subcategory"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job subcategory created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)


class JobSubCategoryListAPIView(BaseMasterAPIView):

    model = JobSubCategory
    serializer_class = JobSubCategorySerializer
    model_name = "Job Subcategory"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True,
            category__is_active=True,
        ).select_related("category").order_by("name")

        # Optional: only subcategories of one category (for dropdowns).
        category_id = request.data.get("category") or request.data.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        serializer = self.serializer_class(queryset, many=True)

        return self.success(
            "Job subcategory list fetched successfully.",
            serializer.data
        )


class JobSubCategoryDetailAPIView(BaseMasterAPIView):

    model = JobSubCategory
    serializer_class = JobSubCategorySerializer
    model_name = "Job Subcategory"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Job subcategory not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Job subcategory fetched successfully.",
            serializer.data
        )


class UpdateJobSubCategoryAPIView(BaseMasterAPIView):

    permission_classes = [IsAdmin]
    model = JobSubCategory
    serializer_class = JobSubCategorySerializer
    model_name = "Job Subcategory"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Job subcategory not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj, data=request.data, partial=True)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job subcategory updated successfully.",
                serializer.data
            )

        return self.validation_error(serializer.errors)


class DeleteJobSubCategoryAPIView(BaseMasterAPIView):

    permission_classes = [IsAdmin]
    model = JobSubCategory
    serializer_class = JobSubCategorySerializer
    model_name = "Job Subcategory"

    def post(self, request):

        obj = self.get_object(request.data.get("id"))

        if not obj:
            return self.error(
                "Job subcategory not found.",
                status.HTTP_404_NOT_FOUND
            )

        # Soft delete: jobs use this subcategory with PROTECT,
        # so a real delete would fail.
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])

        return self.success("Job subcategory deleted successfully.")
        
        
class CreateJobTypeAPIView(BaseMasterAPIView):

    model = JobType
    serializer_class = JobTypeSerializer
    model_name = "Job Type"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job type created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)


class JobTypeListAPIView(BaseMasterAPIView):

    model = JobType
    serializer_class = JobTypeSerializer
    model_name = "Job Type"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Job type list fetched successfully.",
            serializer.data
        )


class JobTypeDetailAPIView(BaseMasterAPIView):

    model = JobType
    serializer_class = JobTypeSerializer
    model_name = "Job Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job type not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Job type fetched successfully.",
            serializer.data
        )


class UpdateJobTypeAPIView(BaseMasterAPIView):

    model = JobType
    serializer_class = JobTypeSerializer
    model_name = "Job Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job type not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Job type updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )


class DeleteJobTypeAPIView(BaseMasterAPIView):

    model = JobType
    serializer_class = JobTypeSerializer
    model_name = "Job Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Job type not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Job type deleted successfully."
        )
        
        
class CreateEducationLevelAPIView(BaseMasterAPIView):

    model = EducationLevel
    serializer_class = EducationLevelSerializer
    model_name = "Education Level"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Education level created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)


class EducationLevelListAPIView(BaseMasterAPIView):

    model = EducationLevel
    serializer_class = EducationLevelSerializer
    model_name = "Education Level"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("display_order", "name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Education level list fetched successfully.",
            serializer.data
        )


class EducationLevelDetailAPIView(BaseMasterAPIView):

    model = EducationLevel
    serializer_class = EducationLevelSerializer
    model_name = "Education Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Education level not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Education level fetched successfully.",
            serializer.data
        )


class UpdateEducationLevelAPIView(BaseMasterAPIView):

    model = EducationLevel
    serializer_class = EducationLevelSerializer
    model_name = "Education Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Education level not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Education level updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )


class DeleteEducationLevelAPIView(BaseMasterAPIView):

    model = EducationLevel
    serializer_class = EducationLevelSerializer
    model_name = "Education Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Education level not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Education level deleted successfully."
        )
        
        
class CreateExperienceLevelAPIView(BaseMasterAPIView):

    model = ExperienceLevel
    serializer_class = ExperienceLevelSerializer
    model_name = "Experience Level"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Experience level created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)


class ExperienceLevelListAPIView(BaseMasterAPIView):

    model = ExperienceLevel
    serializer_class = ExperienceLevelSerializer
    model_name = "Experience Level"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("display_order")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Experience level list fetched successfully.",
            serializer.data
        )


class ExperienceLevelDetailAPIView(BaseMasterAPIView):

    model = ExperienceLevel
    serializer_class = ExperienceLevelSerializer
    model_name = "Experience Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Experience level not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Experience level fetched successfully.",
            serializer.data
        )


class UpdateExperienceLevelAPIView(BaseMasterAPIView):

    model = ExperienceLevel
    serializer_class = ExperienceLevelSerializer
    model_name = "Experience Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Experience level not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Experience level updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )


class DeleteExperienceLevelAPIView(BaseMasterAPIView):

    model = ExperienceLevel
    serializer_class = ExperienceLevelSerializer
    model_name = "Experience Level"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Experience level not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Experience level deleted successfully."
        )
        
        
class CreateEmploymentTypeAPIView(BaseMasterAPIView):

    model = EmploymentType
    serializer_class = EmploymentTypeSerializer
    model_name = "Employment Type"

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Employment type created successfully.",
                serializer.data,
                status.HTTP_201_CREATED
            )

        return self.validation_error(serializer.errors)


class EmploymentTypeListAPIView(BaseMasterAPIView):

    model = EmploymentType
    serializer_class = EmploymentTypeSerializer
    model_name = "Employment Type"

    def post(self, request):

        queryset = self.model.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = self.serializer_class(
            queryset,
            many=True
        )

        return self.success(
            "Employment type list fetched successfully.",
            serializer.data
        )


class EmploymentTypeDetailAPIView(BaseMasterAPIView):

    model = EmploymentType
    serializer_class = EmploymentTypeSerializer
    model_name = "Employment Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Employment type not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(obj)

        return self.success(
            "Employment type fetched successfully.",
            serializer.data
        )


class UpdateEmploymentTypeAPIView(BaseMasterAPIView):

    model = EmploymentType
    serializer_class = EmploymentTypeSerializer
    model_name = "Employment Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Employment type not found.",
                status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return self.success(
                "Employment type updated successfully.",
                serializer.data
            )

        return self.validation_error(
            serializer.errors
        )


class DeleteEmploymentTypeAPIView(BaseMasterAPIView):

    model = EmploymentType
    serializer_class = EmploymentTypeSerializer
    model_name = "Employment Type"

    def post(self, request):

        obj = self.get_object(
            request.data.get("id")
        )

        if not obj:

            return self.error(
                "Employment type not found.",
                status.HTTP_404_NOT_FOUND
            )

        obj.delete()

        return self.success(
            "Employment type deleted successfully."
        )
        

        
        
        
class PincodeLocationLookupAPIView(APIView):
    """
    Looks up official India Post records using a six-digit pincode.
    If more than one post office exists, the frontend shows a dropdown.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        pincode = str(
            request.data.get("pincode", "")
        ).strip()

        if not pincode.isdigit() or len(pincode) != 6:
            return Response(
                {
                    "success": False,
                    "message": "Enter a valid 6-digit pincode.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        locations = PostalLocation.objects.filter(
            pincode=pincode,
            is_active=True,
        ).order_by("post_office")

        serializer = PincodePostalLocationSerializer(
            locations,
            many=True,
        )

        data = serializer.data

        if not data:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No address was found for this pincode."
                    ),
                    "data": [],
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "message": "Pincode details fetched successfully.",
                "requires_selection": len(data) > 1,
                "data": data,
            },
            status=status.HTTP_200_OK,
        )
        
        
                
class SuggestJobCategoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        name = request.data.get("name", "").strip()

        if not name:
            return Response(
                {"success": False, "message": "Category name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(name) < 2:
            return Response(
                {"success": False, "message": "Category name must contain at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized = name.title()

        existing = JobCategory.objects.filter(name__iexact=normalized, is_active=True).first()

        if existing:
            return Response(
                {
                    "success": True,
                    "message": "Category already exists.",
                    "data": JobCategorySerializer(existing).data,
                    "is_new": False,
                },
                status=status.HTTP_200_OK,
            )

        category = JobCategory.objects.create(name=normalized)

        return Response(
            {
                "success": True,
                "message": "New category added successfully.",
                "data": JobCategorySerializer(category).data,
                "is_new": True,
            },
            status=status.HTTP_201_CREATED,
        )


class SuggestJobSubCategoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        category_id = request.data.get("category_id")
        name = request.data.get("name", "").strip()

        if not category_id:
            return Response(
                {"success": False, "message": "category_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = JobCategory.objects.filter(id=category_id, is_active=True).first()

        if not category:
            return Response(
                {"success": False, "message": "Job category not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not name:
            return Response(
                {"success": False, "message": "Subcategory name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(name) < 2:
            return Response(
                {"success": False, "message": "Subcategory name must contain at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized = name.title()

        existing = JobSubCategory.objects.filter(
            category=category, name__iexact=normalized, is_active=True
        ).first()

        if existing:
            return Response(
                {
                    "success": True,
                    "message": "Subcategory already exists.",
                    "data": JobSubCategorySerializer(existing).data,
                    "is_new": False,
                },
                status=status.HTTP_200_OK,
            )

        subcategory = JobSubCategory.objects.create(category=category, name=normalized)

        return Response(
            {
                "success": True,
                "message": "New subcategory added successfully.",
                "data": JobSubCategorySerializer(subcategory).data,
                "is_new": True,
            },
            status=status.HTTP_201_CREATED,
        )

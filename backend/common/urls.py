from django.urls import path

from common.views import *


urlpatterns = [

    # ==========================================
    # 1. STATE CRUD APIs
    # ==========================================

    path("state/create/", CreateStateAPIView.as_view()),
    path("state/list/", StateListAPIView.as_view()),
    path("state/detail/", StateDetailAPIView.as_view()),
    path("state/update/", UpdateStateAPIView.as_view()),
    path("state/delete/", DeleteStateAPIView.as_view()),

    # ==========================================
    # 2. DISTRICT CRUD APIs
    # ==========================================

    path("district/create/", CreateDistrictAPIView.as_view()),
    path("district/list/", DistrictListAPIView.as_view()),
    path("district/detail/", DistrictDetailAPIView.as_view()),
    path("district/update/", UpdateDistrictAPIView.as_view()),
    path("district/delete/", DeleteDistrictAPIView.as_view()),

    # ==========================================
    # 3. TALUKA CRUD APIs
    # ==========================================

    path("taluka/create/", CreateTalukaAPIView.as_view()),
    path("taluka/list/", TalukaListAPIView.as_view()),
    path("taluka/detail/", TalukaDetailAPIView.as_view()),
    path("taluka/update/", UpdateTalukaAPIView.as_view()),
    path("taluka/delete/", DeleteTalukaAPIView.as_view()),

    # ==========================================
    # 4. LOCATION CRUD APIs
    # ==========================================

    path("location/create/", CreateLocationAPIView.as_view()),
    path("location/list/", LocationListAPIView.as_view()),
    path("location/detail/", LocationDetailAPIView.as_view()),
    path("location/update/", UpdateLocationAPIView.as_view()),
    path("location/delete/", DeleteLocationAPIView.as_view()),
    path("location/lookup-by-pincode/", PincodeLocationLookupAPIView.as_view(),),

    # ==========================================
    # 5. SKILL CRUD APIs
    # ==========================================

    path("skill/create/", CreateSkillAPIView.as_view()),
    path("skill/list/", SkillListAPIView.as_view()),
    path("skill/detail/", SkillDetailAPIView.as_view()),
    path("skill/update/", UpdateSkillAPIView.as_view()),
    path("skill/delete/", DeleteSkillAPIView.as_view()),

    # ==========================================
    # 6. LANGUAGE CRUD APIs
    # ==========================================

    path("language/create/", CreateLanguageAPIView.as_view()),
    path("language/list/", LanguageListAPIView.as_view()),
    path("language/detail/", LanguageDetailAPIView.as_view()),
    path("language/update/", UpdateLanguageAPIView.as_view()),
    path("language/delete/", DeleteLanguageAPIView.as_view()),

    # ==========================================
    # 7. JOB CATEGORY CRUD APIs
    # ==========================================

    path("job-category/create/", CreateJobCategoryAPIView.as_view()),
    path("job-category/list/", JobCategoryListAPIView.as_view()),
    path("job-category/detail/", JobCategoryDetailAPIView.as_view()),
    path("job-category/update/", UpdateJobCategoryAPIView.as_view()),
    path("job-category/delete/", DeleteJobCategoryAPIView.as_view()),
    path("job-category/suggest/", SuggestJobCategoryAPIView.as_view()),
    # ==========================================
    # 7A. JOB SUBCATEGORY CRUD APIs
    # ==========================================

    path("job-subcategory/create/", CreateJobSubCategoryAPIView.as_view()),
    path("job-subcategory/list/", JobSubCategoryListAPIView.as_view()),
    path("job-subcategory/detail/", JobSubCategoryDetailAPIView.as_view()),
    path("job-subcategory/update/", UpdateJobSubCategoryAPIView.as_view()),
    path("job-subcategory/delete/", DeleteJobSubCategoryAPIView.as_view()),
    path("job-subcategory/suggest/", SuggestJobSubCategoryAPIView.as_view()),

    # ==========================================
    # 8. JOB TYPE CRUD APIs
    # ==========================================

    path("job-type/create/", CreateJobTypeAPIView.as_view()),
    path("job-type/list/", JobTypeListAPIView.as_view()),
    path("job-type/detail/", JobTypeDetailAPIView.as_view()),
    path("job-type/update/", UpdateJobTypeAPIView.as_view()),
    path("job-type/delete/", DeleteJobTypeAPIView.as_view()),

    # ==========================================
    # 9. EDUCATION LEVEL CRUD APIs
    # ==========================================

    path("education-level/create/", CreateEducationLevelAPIView.as_view()),
    path("education-level/list/", EducationLevelListAPIView.as_view()),
    path("education-level/detail/", EducationLevelDetailAPIView.as_view()),
    path("education-level/update/", UpdateEducationLevelAPIView.as_view()),
    path("education-level/delete/", DeleteEducationLevelAPIView.as_view()),

    # ==========================================
    # 10. EXPERIENCE LEVEL CRUD APIs
    # ==========================================

    path("experience-level/create/", CreateExperienceLevelAPIView.as_view()),
    path("experience-level/list/", ExperienceLevelListAPIView.as_view()),
    path("experience-level/detail/", ExperienceLevelDetailAPIView.as_view()),
    path("experience-level/update/", UpdateExperienceLevelAPIView.as_view()),
    path("experience-level/delete/", DeleteExperienceLevelAPIView.as_view()),

    # ==========================================
    # 11. EMPLOYMENT TYPE CRUD APIs
    # ==========================================

    path("employment-type/create/", CreateEmploymentTypeAPIView.as_view()),
    path("employment-type/list/", EmploymentTypeListAPIView.as_view()),
    path("employment-type/detail/", EmploymentTypeDetailAPIView.as_view()),
    path("employment-type/update/", UpdateEmploymentTypeAPIView.as_view()),
    path("employment-type/delete/", DeleteEmploymentTypeAPIView.as_view()),


]
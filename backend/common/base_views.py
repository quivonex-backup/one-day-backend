from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from accounts.access import IsAdmin


class BaseMasterAPIView(APIView):

    # List / Detail APIs are public (needed for dropdowns).
    # Create / Update / Delete APIs are admin only.
    permission_classes = [AllowAny]
    admin_actions = ("Create", "Update", "Delete")

    model = None
    serializer_class = None
    model_name = ""

    def get_permissions(self):
        if self.__class__.__name__.startswith(self.admin_actions):
            return [IsAdmin()]
        return super().get_permissions()

    def success(self, message, data=None, status_code=status.HTTP_200_OK):

        response = {
            "success": True,
            "message": message,
        }

        if data is not None:
            response["data"] = data

        return Response(response, status=status_code)

    def error(self, message, status_code=status.HTTP_400_BAD_REQUEST):

        return Response(
            {
                "success": False,
                "message": message
            },
            status=status_code
        )

    def validation_error(self, errors):

        return Response(
            {
                "success": False,
                "errors": errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def get_object(self, object_id):

        return self.model.objects.filter(
            id=object_id,
            is_active=True
        ).first()
        
        
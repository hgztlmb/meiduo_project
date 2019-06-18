from rest_framework.views import APIView
from meiduo_admin.serializers.user_login_serializers import UserLoginSerializers
from rest_framework.response import Response

class UserLoginView(APIView):
    def post(self,request):
        serializer = UserLoginSerializers(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            "username": serializer.validated_data.get("user").username,
            "user_id": serializer.validated_data.get("user").id,
            "token": serializer.validated_data.get("jwt_token")
        })
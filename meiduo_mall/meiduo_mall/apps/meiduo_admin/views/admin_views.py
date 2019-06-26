from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.admin_serializers import *
from meiduo_admin.pages import UserPageNum
from rest_framework.response import Response


class AdminViewSet(ModelViewSet):
    queryset = User.objects.filter(is_staff=True)
    serializer_class = AdminSerializer
    pagination_class = UserPageNum

    # GET
    # permission/groups/simple/
    def simple(self, request):
        groups = Group.objects.all()
        s = AdminGroupSerializer(groups, many=True)
        return Response(s.data)

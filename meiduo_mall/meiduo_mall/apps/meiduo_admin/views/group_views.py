from rest_framework.viewsets import ModelViewSet
from django.contrib.auth.models import Group, Permission
from meiduo_admin.serializers.group_serializers import *
from meiduo_admin.pages import UserPageNum
from rest_framework.decorators import action
from rest_framework.response import Response


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    pagination_class = UserPageNum

    # GET
    # permission/simple/
    @action(methods=['get'], detail=False)
    def simple(self, request):
        perms = Permission.objects.all()
        s = PermSimpleSerializer(perms, many=True)
        return Response(s.data)

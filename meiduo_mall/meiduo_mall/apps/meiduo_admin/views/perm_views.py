from rest_framework.viewsets import ModelViewSet
from django.contrib.auth.models import Permission, ContentType
from meiduo_admin.serializers.perm_serializers import *
from meiduo_admin.pages import UserPageNum
from rest_framework.decorators import action
from rest_framework.response import Response


class PermViewSet(ModelViewSet):
    queryset = Permission.objects.order_by('id')
    serializer_class = PermSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        if self.action == "content_types":
            return ContentType.objects.all()
        return self.queryset.all()

    def get_serializer_class(self):
        if self.action == "content_types":
            return ContentTypeSerializer
        return self.serializer_class

    # GET
    # permission/content_types/
    @action(methods=['get'], detail=False)
    def content_types(self, request):
        ctype_queryset = self.get_queryset()
        s = self.get_serializer(ctype_queryset, many=True)
        return Response(s.data)

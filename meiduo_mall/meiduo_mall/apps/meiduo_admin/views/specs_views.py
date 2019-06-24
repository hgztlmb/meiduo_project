# meiduo_admin/goods/specs/?page=1&pagesize=10
from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.specs_serializers import *
from meiduo_admin.pages import UserPageNum
from goods.models import SPUSpecification,SpecificationOption

class SpecsInfoView(ModelViewSet):
    queryset = SPUSpecification.objects.all()
    serializer_class = SpecsInfoSerializer
    pagination_class = UserPageNum


class SpecsOptionsView(ModelViewSet):
    queryset = SpecificationOption.objects.all()
    serializer_class = SpecsOptionsSerializer
    pagination_class = UserPageNum
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.spu_info_serializers import *
from meiduo_admin.pages import UserPageNum

# /meiduo_admin/goods/?keyword=<名称|副标题>&page=<页码>&page_size=<页容量>
from goods.models import *


class SPUView(ModelViewSet):
    queryset = SPU.objects.all()
    serializer_class = SPUInfoSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get("keyword")
        if keyword:
            return self.queryset.filter(name__contains=keyword)
        return self.queryset


class CategoryView(ModelViewSet):
    queryset = GoodsCategory.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        parent = self.kwargs.get("pk")
        if parent:
            return self.queryset.filter(parent_id=parent)
        return self.queryset.filter(parent_id=None)


class BrandView(ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandInfoSerializer
    # pagination_class = UserPageNum

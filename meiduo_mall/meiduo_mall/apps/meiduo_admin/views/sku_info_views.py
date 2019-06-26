from rest_framework.generics import *
from rest_framework.viewsets import ModelViewSet
from goods.models import *
from meiduo_admin.pages import UserPageNum
from meiduo_admin.serializers.sku_info_serializers import *


class SKUInfoView(ModelViewSet):
    queryset = SKU.objects.all()
    serializer_class = SKUInfoSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get("keyword")
        if keyword:
            return self.queryset.filter(name__contains=keyword)
        else:
            return self.queryset.all()



class CategoryInfoView(ListAPIView):
    queryset = GoodsCategory.objects.filter(parent_id__gt=37)
    serializer_class = CategoryInfoSerializer


class SPUInfoView(ListAPIView):
    queryset = SPU.objects.all()
    serializer_class = SPUInfoSerializer


class SPUSpecView(ListAPIView):
    queryset = SPUSpecification.objects.all()
    serializer_class = SPUSpecSerializer

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        if pk:
            return self.queryset.filter(spu_id=pk)
        else:
            return self.queryset.all()

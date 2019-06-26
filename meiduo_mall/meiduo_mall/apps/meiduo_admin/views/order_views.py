from rest_framework.viewsets import ModelViewSet
from orders.models import OrderInfo
from meiduo_admin.serializers.order_serializers import *
from meiduo_admin.pages import UserPageNum


class OrderView(ModelViewSet):
    queryset = OrderInfo.objects.all()
    serializer_class = OrderSimpleSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get("keyword")
        if keyword:
            return self.queryset.filter(order_id__contains=keyword)
        return self.queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderSerializer
        return self.serializer_class
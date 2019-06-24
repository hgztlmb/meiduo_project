from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.channel_serializers import *
from meiduo_admin.pages import UserPageNum
from goods.models import GoodsChannel


class ChannelView(ModelViewSet):
    queryset = GoodsChannel.objects.all()
    serializer_class = ChannelSerializer
    pagination_class = UserPageNum

class ChannelGroupView(ModelViewSet):
    queryset = GoodsChannelGroup.objects.all()
    serializer_class = ChannelGroupSerializer

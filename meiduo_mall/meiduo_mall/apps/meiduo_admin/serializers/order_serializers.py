from rest_framework import serializers

from goods.models import SKU
from orders.models import OrderInfo,OrderGoods

class OrderSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfo
        fields = [
            "order_id",
            "create_time",
            "status"
        ]




class SKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = "__all__"


class OrderDetailSerializer(serializers.ModelSerializer):
    sku = SKUSerializer(read_only=True)
    class Meta:
        model = OrderGoods
        fields = "__all__"



class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    skus = OrderDetailSerializer(many=True,read_only=True)

    class Meta:
        model = OrderInfo
        fields = "__all__"
from rest_framework import serializers
from goods.models import GoodsVisitCount


class GoodSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = GoodsVisitCount
        fields = ('count', 'category')

from rest_framework import serializers

from goods.models import *


class BrandInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name")


class SPUInfoSerializer(serializers.ModelSerializer):
    brand = serializers.StringRelatedField()
    brand_id = serializers.IntegerField()
    category1_id = serializers.IntegerField()
    category2_id = serializers.IntegerField()
    category3_id = serializers.IntegerField()

    class Meta:
        model = SPU

        exclude = ['category1','category2','category3']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsCategory
        fields = "__all__"
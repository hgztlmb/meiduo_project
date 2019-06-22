from rest_framework import serializers

from goods.models import *


class SpecsSerializer(serializers.ModelSerializer):
    spec_id = serializers.IntegerField()
    option_id = serializers.IntegerField()

    class Meta:
        model = SKUSpecification
        fields = ('spec_id', 'option_id')


class SKUInfoSerializer(serializers.ModelSerializer):
    spu = serializers.StringRelatedField()
    spu_id = serializers.IntegerField()
    category = serializers.StringRelatedField()
    category_id = serializers.IntegerField()
    specs = SpecsSerializer(many=True, read_only=True)

    class Meta:
        model = SKU
        fields = "__all__"


class CategoryInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsCategory
        fields = ('id', 'name')


class SPUInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SPU
        fields = ('id', 'name')


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationOption
        fields = ('id', 'value')


class SPUSpecSerializer(serializers.ModelSerializer):
    spu = serializers.StringRelatedField()
    spu_id = serializers.IntegerField()
    options = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = SPUSpecification
        fields = ('id', 'name', 'spu_id', 'spu', 'options')

from rest_framework import serializers
from goods.models import SKUImage,SKU
from fdfs_client.client import Fdfs_client




class ImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = SKUImage
        fields = [
            'id',
            'sku', # PrimaryKeyRelatedField(queryset=SKU.objects.all())
            'image'
        ]


    def create(self, validated_data):
        """
        新建图片对象的时候，上传图片到fdfs逻辑
        :param validated_data:
        :return:
        """

        # image就是校验过后的"图片对象"
        image = validated_data.pop('image')

        # 1、获得fdfs链接对象
        conn = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")
        # 2、上传文件
        content = image.read()  # bytes
        result = conn.upload_by_buffer(content)

        # 3、判断是否上传成功
        if not result.get("Status") == "Upload successed.":
            raise serializers.ValidationError("上传失败")

        # 4、如果成功，获得fdfs文件标示
        url = result.get("Remote file_id")

        validated_data['image'] = url
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # image就是校验过后的"图片对象"
        image = validated_data.pop('image')

        # 1、获得fdfs链接对象
        conn = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")
        # 2、上传文件
        content = image.read()  # bytes
        result = conn.upload_by_buffer(content)

        # 3、判断是否上传成功
        if not result.get("Status") == "Upload successed.":
            raise serializers.ValidationError("上传失败")

        # 4、如果成功，获得fdfs文件标示
        url = result.get("Remote file_id")

        validated_data['image'] = url
        return super().update(instance, validated_data)


class SKUSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = [
            'id',
            'name'
        ]
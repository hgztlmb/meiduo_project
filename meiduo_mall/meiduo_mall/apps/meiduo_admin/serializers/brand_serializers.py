from fdfs_client.client import Fdfs_client
from rest_framework import serializers
from goods.models import Brand


class BrandAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"

    def create(self, validated_data):
        logo = validated_data.pop("logo")
        content = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")

        result = content.upload_by_buffer(logo.read())
        if not result.get('Status') == "Upload successed.":
            raise serializers.ValidationError("上传失败")
        url = result.get("Remote file_id")
        validated_data['logo'] = url
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logo = validated_data.pop("logo")
        content = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")

        result = content.upload_by_buffer(logo.read())
        if not result.get('Status') == "Upload successed.":
            raise serializers.ValidationError("上传失败")
        url = result.get("Remote file_id")
        instance.logo = url
        instance.save()
        return instance
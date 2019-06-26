from rest_framework import serializers
from django.contrib.auth.models import Permission, ContentType


class PermSerializer(serializers.ModelSerializer):
    # content_type = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Permission
        fields = [
            'id',
            'name',
            'codename',
            'content_type'
        ]


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'name']

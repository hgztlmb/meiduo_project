from rest_framework import serializers
from django.contrib.auth.models import Group, Permission


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id',
            'name',

            'permissions'
        ]


class PermSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = [
            'id',
            'name'
        ]

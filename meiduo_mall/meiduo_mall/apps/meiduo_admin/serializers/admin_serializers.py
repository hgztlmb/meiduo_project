from rest_framework import serializers
from users.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.hashers import make_password


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'mobile',

            'password',
            'groups',
            'user_permissions'
        ]

        extra_kwargs = {
            'password': {
                "write_only": True,
            },
        }

    def create(self, validated_data):

        # validated_data['password'] = make_password(validated_data['password'])
        # validated_data['is_staff'] = True
        # # 密码未加密
        # return super().create(validated_data)

        # 1、提取manytomanyfields
        groups = validated_data.pop('groups')  # [5]
        user_permissions = validated_data.pop('user_permissions')  # [79, 80]

        # 2、新建主表对象
        admin_user = User.objects.create_superuser(**validated_data)

        # 3、构建中间表数据
        admin_user.groups.set(groups)
        admin_user.user_permissions.set(user_permissions)

        return admin_user

    def update(self, instance, validated_data):
        # 校验密码是否传入
        # 如果传入,加密
        # 没有传入

        password = validated_data.get("password")
        if password:
            validated_data['password'] = make_password(password)
        else:
            validated_data['password'] = instance.password

        return super().update(instance, validated_data)


class AdminGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

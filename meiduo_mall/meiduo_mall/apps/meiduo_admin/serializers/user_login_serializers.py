from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_jwt.utils import jwt_payload_handler, jwt_encode_handler


class UserLoginSerializers(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(**attrs)

        if not user:
            raise serializers.ValidationError("用户认证失败")

        payload = jwt_payload_handler(user)
        jwt_token = jwt_encode_handler(payload)

        return {
            "user": user,
            "jwt_token": jwt_token
        }

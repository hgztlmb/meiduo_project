from rest_framework import serializers

from users.models import User


class UserAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email','password')

        extra_kwargs = {
            'id': {"read_only": True},
            'password': {"write_only": True}
        }

    def create(self, validated_data):
        return self.Meta.model.objects.create_superuser(**validated_data)

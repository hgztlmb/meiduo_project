from rest_framework.generics import ListAPIView, CreateAPIView
from meiduo_admin.pages import UserPageNum
from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.user_admin_serializers import UserAdminSerializer
from users.models import User


class UserAdminView(ModelViewSet):
    serializer_class = UserAdminSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            return User.objects.filter(username__contains=keyword)
        else:
            return User.objects.all()

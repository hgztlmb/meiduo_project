from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from meiduo_admin.serializers.user_admin_serializers import UserAdminSerializer
from users.models import User

# meiduo_admin/users/?keyword=<搜索内容>&page=<页码>&pagesize=<页容量>
class UserPageNum(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'pagesize'
    max_page_size = 10

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "lists": data,
            "page": self.page.number,
            "pages": self.page.paginator.num_pages,
            "pagesize": self.page_size
        })


class UserAdminView(ListAPIView,CreateAPIView):
    serializer_class = UserAdminSerializer
    pagination_class = UserPageNum

    def get_queryset(self):
        keyword = self.request.query_params.get('keyword')
        if keyword:
            return User.objects.filter(username__contains=keyword)
        else:
            return User.objects.all()

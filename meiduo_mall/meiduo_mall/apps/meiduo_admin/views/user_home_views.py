from datetime import timedelta
from meiduo_admin.serializers.user_home_serializers import GoodSerializer
import pytz
from django.conf import settings

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.utils import timezone

from users.models import User
from goods.models import GoodsVisitCount


class UserHomeView(ViewSet):

    @action(methods=['get'], detail=False)
    def total_count(self, request):
        """
        用户总量
        :param request:
        :return: count: 总数,
                 date:  日期
        """
        count = User.objects.filter(is_active=True).count()
        date = timezone.now()
        return Response({
            "count": count,
            "date": date
        })

    @action(methods=["get"], detail=False)
    def day_increment(self, request):
        """
        日增用户
        :param request:
        :return: count: 总量,
                 date:  日期
        """
        date = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))
        count = User.objects.filter(date_joined__gte=date.replace(hour=0, minute=0, second=0)).count()
        return Response({
            "count": count,
            "date": date
        })

    @action(methods=["get"], detail=False)
    def day_active(self, request):
        """
        日活跃用户
        :param request:
        :return: count: 总数,
                 date:  日期
        """
        date = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))
        count = User.objects.filter(last_login__gte=date.replace(hour=0, minute=0, second=0)).count()
        return Response({
            "count": count,
            "date": date
        })

    @action(methods=['get'], detail=False)
    def day_orders(self, request):
        """
        日下单用户量
        :param request:
        :return: count: 总数,
                 date:  日期
        """
        date = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))
        count_list = User.objects.filter(orderinfo__create_time__gte=date.replace(hour=0, minute=0, second=0))
        count = len(set(count_list))
        return Response({
            "count": count,
            "date": date
        })

    @action(methods=["get"], detail=False)
    def month_increment(self, request):
        """
        月增用户统计
        :param request:
        :return:    [
                    {
                        "count": "用户量",
                        "date": "日期"
                    },
                    {
                        "count": "用户量",
                        "date": "日期"
                    },
                    ...
                    ]
        """
        now_date = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))
        start_date = (now_date - timedelta(days=29)).replace(hour=0, minute=0, second=0)
        user_list = []
        for days in range(30):
            date = start_date + timedelta(days=days)
            count = User.objects.filter(date_joined__gte=date, date_joined__lt=date + timedelta(days=1)).count()
            user_list.append({
                "count": count,
                "date": date.date()
            })
        return Response(user_list)

    @action(methods=["get"], detail=False)
    def goods_day_views(self, request):
        """
        日商品访问量
        :param request:
        :return:    [
                    {
                        "category": "分类名称",
                        "count": "访问量"
                    },
                    {
                        "category": "分类名称",
                        "count": "访问量"
                    },
                    ...
                    ]
        """
        date = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))
        data = GoodsVisitCount.objects.filter(date=date)
        ser = GoodSerializer(data, many=True)
        return Response(ser.data)



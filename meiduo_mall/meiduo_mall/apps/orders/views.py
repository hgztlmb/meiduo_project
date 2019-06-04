from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import mixins
from django_redis import get_redis_connection
from goods.models import SKU
from decimal import Decimal
from users.models import Address


class OrderSettlementView(mixins.LoginRequiredMixin, View):
    """结算界面展示"""

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return redirect("/login/")
        else:
            addresses = Address.objects.filter(user=request.user, is_deleted=False)
            addresses = addresses if addresses.exists() else None
            # 获取redis信息
            redis_conn = get_redis_connection("carts")
            redis_dict = redis_conn.hgetall("carts_%s" % user.id)
            redis_ids = redis_conn.smembers("selected_%s" % user.id)
            # 定义字典保存数据
            cart_dict = {}
            # 遍历set包装打钩的商品
            for sku in redis_ids:
                cart_dict[int(sku)] = int(redis_dict[sku])
            # 获取勾选商品的sku模型
            sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
            total_amount = Decimal('0.00')
            total_count = 0

            # 遍历查询集并给sku对象添加属性
            for sku in sku_qs:
                sku.count = cart_dict[sku.id]
                sku.amount = sku.price * sku.count

                total_amount += sku.amount
                total_count += sku.count

            # 运费
            freight = Decimal('10.00')

            # 包装数据
            context = {
                "addresses": addresses,
                "skus": sku_qs,
                "total_count": total_count,
                "total_amount": total_amount,
                "freight": freight,
                "payment_amount": total_amount + freight
            }
            return render(request,"place_order.html",context)





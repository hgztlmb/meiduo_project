from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import mixins
from django_redis import get_redis_connection
from goods.models import SKU
from decimal import Decimal
from users.models import Address
from meiduo_mall.utils.view import LoginRequiredView
import json
from django import http
from meiduo_mall.utils.response_code import RETCODE
from .models import OrderInfo, OrderGoods
from django.utils import timezone
from django.db import transaction


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
            # redis_conn.delete("selected_%s" % user.id, )
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
            return render(request, "place_order.html", context)


class OrderCommitView(LoginRequiredView):
    """订单提交"""

    def post(self, request):
        # 　获取数据
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get("address_id")
        pay_method = json_dict.get("pay_method")
        # 校验
        if all([address_id, pay_method]) is False:
            return http.HttpResponseForbidden("缺少必传参数")
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden("地址不存在")
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM["CASH"], OrderInfo.PAY_METHODS_ENUM["ALIPAY"]]:
            return http.HttpResponseForbidden("支付方式错误")
        user = request.user
        # 生成订单号 时间+user_id
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        status = (OrderInfo.ORDER_STATUS_ENUM["UNPAID"]
                  if pay_method == OrderInfo.PAY_METHODS_ENUM["ALIPAY"]
                  else OrderInfo.ORDER_STATUS_ENUM["UNSEND"])

        # 开启事务
        with transaction.atomic():
            # 保存记录点
            save_point = transaction.savepoint()
            # try保存订单记录
            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal(0.00),
                    freight=Decimal("10.00"),
                    pay_method=pay_method,
                    status=status
                )
                # 修改sku库存和销量
                # 连接redis数据库
                redis_conn = get_redis_connection("carts")
                # 获取hash和set数据
                redis_dict = redis_conn.hgetall("carts_%s" % user.id)

                selected_ids = redis_conn.smembers("selected_%s" % user.id)
                if not selected_ids:
                    # 遍历set包装id和count为字典

                    transaction.savepoint_rollback(save_point)
                    return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "购物车为空"})
                carts_dict = {}
                for sku in selected_ids:
                    carts_dict[int(sku)] = int(redis_dict[sku])
                # 遍历字典逐个获取sku模型
                for sku_id in carts_dict:
                    while True:
                        sku_model = SKU.objects.get(id=sku_id)
                        # 获取count
                        buy_count = carts_dict[sku_id]
                        # 定义原始库存和销量
                        origin_stock = sku_model.stock
                        origin_sales = sku_model.sales
                        # 判断count是否超过库存
                        if buy_count > origin_stock:
                            # 超过则回滚并提前响应
                            transaction.savepoint_rollback(save_point)
                            return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "库存不足"})
                        # 计算新库存和销量
                        new_stock = origin_stock - buy_count
                        new_sales = origin_sales + buy_count
                        # 乐观锁修改sku库存和销量
                        result = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                          sales=new_sales)
                        if result == 0:
                            continue
                        # 修改spu销量
                        spu = sku_model.spu
                        spu.sales += buy_count
                        spu.save()
                        # 保存订单信息
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku_model,
                            count=buy_count,
                            price=sku_model.price
                        )
                        # 累加total_count
                        order.total_count += buy_count
                        # 累加total_amount
                        order.total_amount += (buy_count * sku_model.price)
                        # 一个商品购买成功继续下一个
                        break
                # 加运费
                order.total_amount += order.freight
                order.save()
            except Exception:
                transaction.savepoint_rollback(save_point)
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "下单失败"})
                # 提交事物
            else:
                transaction.savepoint_commit(save_point)

                # 删除购物车数据
                pl = redis_conn.pipeline()
                pl.hdel("carts_%s" % user.id, *selected_ids)
                pl.delete("selected_%s" % user.id, )
                pl.execute()

            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "下单成功", "order_id": order_id})


class OrderSuccessView(LoginRequiredView):
    """订单提交成功界面"""

    def get(self, request):
        query_dict = request.GET
        order_id = query_dict.get("order_id")
        payment_amount = query_dict.get("payment_amount")
        pay_method = query_dict.get("pay_method")
        try:
            OrderInfo.objects.get(order_id=order_id, pay_method=pay_method, total_amount=payment_amount)
        except Exception:
            return http.HttpResponseForbidden("订单有误")
        context = {
            "order_id": order_id,
            "payment_amount": payment_amount,
            "pay_method": pay_method
        }
        return render(request, "order_success.html", context)


class OrderCommentView(LoginRequiredView, View):
    """评价界面"""
    def get(self, request):
        query_dict = request.GET
        order_id = query_dict.get("order_id")
        try:
            orders = OrderGoods.objects.filter(order_id=order_id,is_commented=False)
        except OrderGoods.DoesNotExist:
            return http.HttpResponseForbidden("订单未找到")
        sku_list = []
        for sku_qs in orders:
            sku_model = SKU.objects.get(id=sku_qs.sku_id)
            sku_list.append({
                "price": str(sku_model.price),
                "name": sku_model.name,
                "display_score": sku_qs.score,
                # "is_anonymous": "false",
                # "is_anonymous": sku_qs.is_anonymous.lower(),
                # "comment": sku_qs.comment,
                "default_image_url": sku_model.default_image.url,
                "order_id": order_id,
                "sku_id": sku_qs.sku_id

            })

        context = {
            "uncomment_goods_list": sku_list
        }

        return render(request, "goods_judge.html", context)

    def post(self, request):
        """提交评论"""
        json_dict = json.loads(request.body.decode())
        order_id = json_dict.get("order_id")
        sku_id = json_dict.get("sku_id")
        comment = json_dict.get("comment")
        score = json_dict.get("score")
        is_anonymous = json_dict.get("is_anonymous")
        if all([order_id, sku_id, comment, score]) is False:
            return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "缺少必传参数"})
        try:
            sku = OrderGoods.objects.get(order_id=order_id, sku_id=sku_id)
        except OrderGoods.DoesNotExist:
            return http.JsonResponse({"code":RETCODE.DBERR,"errmsg":"评论失败"})
        sku.comment = comment
        sku.score = score
        sku.is_anonymous = is_anonymous
        sku.is_commented = True
        sku.sku.comments += 1
        sku.sku.spu.comments += 1
        sku.save()
        comments = OrderInfo.objects.get(order_id=order_id)
        comments.status = 5
        comments.save()


        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "提交成功"})



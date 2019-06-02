from django.shortcuts import render
from django.views import View
import json, pickle, base64
from django import http
from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection


class CarsView(View):
    """添加购物车"""

    def post(self, request):
        #  获取前端数据
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        count = json_dict.get("count")
        selected = json_dict.get("selected", True)
        # 校验
        if all([sku_id, count, selected]) is False:
            return http.HttpResponseForbidden("缺少必传参数")
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku_id不存在")
        if isinstance(count, int) is False:
            return http.HttpResponseForbidden("类型有误")
        # 获取user判断是否登录
        user = request.user
        if user.is_authenticated:
            # 如果用户登录
            # 创建redis数据库连接对象
            redis_conn = get_redis_connection("carts")
            pl = redis_conn.pipeline()
            # 向redis中添加hash类型数据保存商品id及count信息
            pl.hincrby("carts_%s" % user.id, sku_id, count)
            # 添加set类型数据保存selected信息(selected=True的sku_id)
            if selected == True:
                pl.sadd("selected_%s" % user.id, sku_id)
            pl.execute()
            # 响应
            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "添加购物车成功"})



        else:
            # 如果未登录
            # 从cookie中获取购物车数据
            cart_str = request.COOKIES.get("carts")
            # 如果存在则转换回字典
            if cart_str:
                # 先将字符串转为bytes字符串
                cart_str_bytes = cart_str.encode()
                # 用base64将bytes字符串转为bytes类型
                cart_bytes = base64.b64decode(cart_str_bytes)
                # 用pickle转为字典
                cart_dict = pickle.loads(cart_bytes)
            # 如果不存在
            else:
                # 创建字典
                cart_dict = {}
            # 判断本次添加商品在字典中是否已存在
            if sku_id in cart_dict:
                # 如果存在则商品count+购物车中的count
                origin_count = cart_dict[sku_id]["count"]
                count += origin_count
                # 如果不存在则直接加入字典

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 字典base64,pickle转为字符串
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 创建响应对象
            response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "添加购物车成功"})
            # 设置cookies
            response.set_cookie("carts", cart_str)
            return response

    def get(self, request):
        """购物车展示"""
        # 获取用户信息
        user = request.user
        # 判断用户是否登录
        if user.is_authenticated:
            # 如果登录
            redis_conn = get_redis_connection("carts")
            # 提取redis数据库中hash字典数据
            redis_dict = redis_conn.hgetall("carts_%s" % user.id)
            # 提取redis中set数据
            selected_ids = redis_conn.smembers("selected_%s" % user.id)
            # 设置格式与cookies一致
            # 定义一个字典包装redis数据
            cart_dict = {}
            for carts in redis_dict:
                cart_dict[int(carts)] = {
                    'count': int(redis_dict[carts]),
                    'selected': carts in selected_ids
                }

        else:
            # 如果未登录
            cart_str = request.COOKIES.get("carts")
            # 字符串解码转为字典
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            # 如果为空则直接返回购物车页面
            else:
                return render(request, "cart.html")
        # 获取sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        # 定义列表包装所有数据
        cart_list = []
        for sku_model in sku_qs:
            count = cart_dict[sku_model.id]['count']
            cart_list.append({
                'id': sku_model.id,
                'name': sku_model.name,
                'price': str(sku_model.price),
                'default_image_url': sku_model.default_image.url,
                'count': count,
                'selected': str(cart_dict[sku_model.id]['selected']),
                'amount': str(sku_model.price * count)
            })
        context = {
            'cart_skus': cart_list
        }
        return render(request, "cart.html", context)

    def put(self, request):
        """修改购物车"""
        # 获取数据

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        count = json_dict.get("count")
        selected = json_dict.get("selected")
        # 校验
        if all([sku_id, count]) is False:
            return http.HttpResponseForbidden("缺少必传参数")
        try:
            sku_model = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku_id不存在")
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden("类型错误")
        if not isinstance(selected, bool):
            return http.HttpResponseForbidden("类型错误")
        # 判断是否登录
        user = request.user
        if user.is_authenticated:
            #  修改数据
            redis_conn = get_redis_connection("carts")
            pl = redis_conn.pipeline()
            pl.hset("carts_%s" % user.id, sku_id, count)
            if selected:
                pl.sadd("selected_%s" % user.id, sku_id)
            else:
                pl.srem("selected_%s" % user.id, sku_id)
            pl.execute()

        else:
            # 未登录
            # 获取cookies,转换为字典
            carts_str = request.COOKIES.get("carts")
            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "获取数据失败"})
            # 修改字典数据
            carts_dict[sku_id] = {
                "count": count,
                "selected": selected
            }
            # 转换回字符串
            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()

        # 包装数据为字典
        cart_sku = {
            'id': sku_model.id,
            'name': sku_model.name,
            'price': str(sku_model.price),
            'default_image_url': sku_model.default_image.url,
            'count': count,
            'selected': selected,
            'amount': str(sku_model.price * count)
        }
        # 设置响应对象和cookies
        response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "修改成功", "cart_sku": cart_sku})
        if not user.is_authenticated:
            response.set_cookie("carts", carts_str)
        return response

    def delete(self, request):
        """删除购物车"""
        # 接收
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        # 校验
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("sku.id不存在")
        # 判断
        user = request.user
        if user.is_authenticated:
            # 登录用户通过操作redis数据库删除
            redis_conn = get_redis_connection("carts")
            pl = redis_conn.pipeline()
            # 删除hash对应值
            pl.hdel("carts_%s" % user.id, sku_id)
            # 删除set对应值
            pl.srem("selected_%s" % user.id, sku_id)
            pl.execute()
            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "删除成功"})
        else:
            # 未登录用户删除coookies对应值
            carts_str = request.COOKIES.get("carts")
            if carts_str:
                carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "cookie获取失败"})
            if sku_id in carts_dict:
                del carts_dict[sku_id]

            # 设置响应对象
            response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "删除成功"})
            # 判断carts_dict是否为空,为空则删除cookies
            if not carts_dict:
                response.delete_cookie("carts")
                return response

            carts_str = base64.b64encode(pickle.dumps(carts_dict)).decode()
            response.set_cookie("carts", carts_str)
            return response


class CartsSelectAllView(View):
    """全部选择"""

    def put(self, request):
        # 获取数据
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get("selected")
        # 校验
        if isinstance(selected, bool) is False:
            return http.HttpResponseForbidden("类型错误")
            # 判断登录
        user = request.user
        if user.is_authenticated:
            # 获取hash数据
            redis_conn = get_redis_connection("carts")
            sku_model = redis_conn.hgetall("carts_%s" % user.id)
            if selected:
                # 全选则全部key加入set
                redis_conn.sadd("selected_%s" % user.id, *sku_model.keys())
            # 否则将set清空
            else:
                redis_conn.delete("selected_%s" % user.id)
            return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})
        else:
            # 获取cookies数据
            carts_str = request.COOKIES.get("carts")
            # 转为字典
            if carts_str:
                carts_dic = pickle.loads(base64.b64decode(carts_str.encode()))
            else:
                return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "获取cookies失败"})
            # 设置selected为True或False
            carts_dic[selected] = selected
            # 转回cookies字符串
            carts_str = base64.b64encode(pickle.dumps(carts_dic)).decode()
            # 响应
            response = http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})
            response.set_cookie("carts", carts_str)
            return response


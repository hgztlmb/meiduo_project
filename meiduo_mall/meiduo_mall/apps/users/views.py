from random import randint
from celery_tasks.sms.tasks import send_sms_code
from django.shortcuts import render, redirect
from django import http
from django.views import View
import re, json, logging
from django.contrib.auth import login, authenticate, logout, mixins
from django.core.paginator import Paginator, EmptyPage
from goods.models import SKU
from oauth.utils import generate_openid_signature, check_openid_signature
from orders.models import OrderInfo, OrderGoods
from .utils import generate_email_verify_url, check_verify_token
from .models import User, Address
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection
from django.conf import settings
from celery_tasks.email.tasks import send_verify_email
from meiduo_mall.utils.view import LoginRequiredView
from carts.utils import merge_cart_cookie_to_redis

logger = logging.getLogger('django')


class RegisterView(View):
    """展示注册界面"""

    def get(self, request):

        return render(request, 'register.html')

    # 获取注册信息
    def post(self, request):
        query_dict = request.POST
        username = query_dict.get('username')
        password = query_dict.get('password')
        password2 = query_dict.get('password2')
        mobile = query_dict.get('mobile')
        sms_code = query_dict.get('sms_code')
        allow = query_dict.get('allow')
        # 校验注册信息
        if all([username, password, mobile, sms_code, allow]) is False:
            return http.HttpResponse("缺少必要参数")
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponse("请输入5-20个字符的用户名")
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponse("请输入8-20位密码")
        if not password == password2:
            return http.HttpResponse("两次密码输入不一致")
        if not re.match(r'^1[3456789]\d{9}$', mobile):
            return http.HttpResponse("您输入的手机号格式不正确")
        # 校验短信验证码
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get("sms_%s" % mobile)
        redis_conn.delete("sms_%s" % mobile)
        if sms_code_server is None:
            return http.HttpResponse("短信验证码过期")
        sms_code_server = sms_code_server.decode()
        if sms_code_server != sms_code:
            return http.HttpResponse("短信验证码输入错误")
        # 创建用户并加密密码
        user = User.objects.create_user(username=username, password=password, mobile=mobile)
        # 保留登录状态
        login(request, user)
        # 返回主页
        response = redirect('/')
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
        return response


class UsernameCountView(View):
    """检查用户名是否重复"""

    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        response_data = {'count': count, 'code': RETCODE.OK, 'errmsg': 'ok'}
        return http.JsonResponse(response_data)


class MobileCountView(View):
    """检查手机号是否重复"""

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        response_data = {'count': count, 'code': RETCODE.OK, 'errmsg': 'ok'}
        return http.JsonResponse(response_data)


# 登录界面
class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    # 获取登录信息
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 认证用户名和密码（有一个为None即返回None）
        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        # 保持登录状态
        login(request, user)
        # 设置未勾选记住密码时session为关闭浏览器即失效
        if remember != 'on':
            request.session.set_expiry(0)
        # 判断请求来源（url字符串查询）
        next = request.GET.get('next')
        if next == "/orders/settlement/":
            merge_cart_cookie_to_redis(request)
            response = redirect('/carts/')
        else:
            response = redirect(next or '/')
        # 设置cookie
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE if remember else None)
        response.delete_cookie("carts")
        return response


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        logout(request)

        response = redirect('/login/')
        response.delete_cookie('username')
        return response


class UserInfoView(mixins.LoginRequiredMixin, View):
    """mixins扩展用来返回进入登录页面之前的页面"""

    def get(self, request):
        return render(request, 'user_center_info.html')


class EmailView(View):
    """设置邮箱"""

    # 接受请求
    def put(self, request):
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        # 校验
        if not email:
            return http.JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必要参数'})
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.JsonResponse({'code': RETCODE.EMAILERR, 'errmsg': '邮箱错误'})
        # 修改邮箱字段
        user = request.user
        User.objects.filter(username=user.username, email='').update(email=email)
        # 生成激活链接
        verify_url = generate_email_verify_url(user)
        print(verify_url)
        # celery 异步发邮件
        send_verify_email.delay(email, verify_url)
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮件成功'})


class VerifyEmailUrl(View):
    """邮箱激活"""

    def get(self, request):
        token = request.GET.get('token')  # 获取token
        # 校验
        if token is None:
            return http.HttpResponseForbidden("缺少token")
        # 解密token并获取user
        user = check_verify_token(token)
        if user is None:
            return http.HttpResponseForbidden("token无效")
        # 设置email_active为True
        user.email_active = True
        user.save()
        return redirect('/info/')


class AddressView(LoginRequiredView):
    """收货地址页面展示"""

    def get(self, request):
        user = request.user
        # 查询所有收货地址
        address_qs = Address.objects.filter(user=user, is_deleted=False)
        # 定义列表包装地址字典数据
        address_list = []
        for address_model in address_qs:
            address_list.append({
                'id': address_model.id,
                'title': address_model.title,
                'receiver': address_model.receiver,
                'province': address_model.province.name,
                'province_id': address_model.province.id,
                'city': address_model.city.name,
                'city_id': address_model.city.id,
                'district': address_model.district.name,
                'district_id': address_model.district.id,
                'place': address_model.place,
                'mobile': address_model.mobile,
                'tel': address_model.tel,
                'email': address_model.email
            })
        # print(address_list)
        # 外层包装
        context = {
            'addresses': address_list,
            'default_address_id': user.default_address_id
        }
        # print(context)
        # 渲染
        return render(request, 'user_center_site.html', context)


class CreateAdderssView(LoginRequiredView):
    """新增地址"""

    def post(self, request):
        # 地址不能超过20个
        user = request.user
        count = Address.objects.filter(user=user, is_deleted=False).count()
        if count >= 20:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超出上限'})
        # 接收数据
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden("缺少必要参数")
        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden("mobile格式错误")
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden("tel格式错误")
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden("email格式错误")
        # 保存数据
        try:
            address_model = Address.objects.create(
                user=request.user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '新增地址失败'})
        # 没有默认地址则设为默认地址
        if user.default_address is None:
            user.default_address = address_model
            user.save()
        # 　数据转换为字典
        address_dict = {
            'id': address_model.id,
            'title': address_model.title,
            'receiver': address_model.receiver,
            'province_id': address_model.province.id,
            'province': address_model.province.name,
            'city_id': address_model.city.id,
            'city': address_model.city.name,
            'district_id': address_model.district.id,
            'district': address_model.district.name,
            'place': address_model.place,
            'mobile': address_model.mobile,
            'tel': address_model.tel,
            'email': address_model.email
        }
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address': address_dict})


class UpdateDestroyAddressView(LoginRequiredView):
    """修改删除收货地址"""

    def put(self, request, address_id):
        """接收请求体数据"""
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden("缺少必要参数")
        if not re.match(r'^1[345789]\d{9}$', mobile):
            return http.HttpResponseForbidden("mobile格式错误")
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden("tel格式错误")
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden("email格式错误")
                # 修改
        try:
            Address.objects.filter(id=address_id).update(
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '修改失败'})
        # 获取修改后模型对象
        address_model = Address.objects.get(id=address_id)
        address_dict = {
            'id': address_model.id,
            'title': address_model.title,
            'receiver': address_model.receiver,
            'province_id': address_model.province.id,
            'province': address_model.province.name,
            'city_id': address_model.city.id,
            'city': address_model.city.name,
            'district_id': address_model.district.id,
            'district': address_model.district.name,
            'place': address_model.place,
            'mobile': address_model.mobile,
            'tel': address_model.tel,
            'email': address_model.email
        }
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改地址成功', 'address': address_dict})

    def delete(self, request, address_id):
        """删除地址"""
        # 获取删除address_id
        try:
            address = Address.objects.get(id=address_id)
            # 修改数据库中is_delete为True
            address.is_deleted = True
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': 'address_id不存在'})
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class DefaultAddressView(LoginRequiredView):
    """修改默认收货地址"""

    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)
            user = request.user
            user.default_address = address
            user.save()
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '设置默认地址失败'})


class UpdateAddressTitleView(LoginRequiredView):
    """修改收货地址标题"""

    def put(self, request, address_id):
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        if title is None:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '缺少必传参数'})
        try:
            address = Address.objects.get(id=address_id)
            address.title = title
            address.save()
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改成功'})
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '修改失败'})


class ChangePasswordView(LoginRequiredView):
    """修改密码"""

    def get(self, request):
        """展示界面"""
        return render(request, 'user_center_pass.html')

    def post(self, request):
        """接收表单"""
        query_dict = request.POST
        old_pwd = query_dict.get('old_pwd')
        new_pwd = query_dict.get('new_pwd')
        new_cpwd = query_dict.get('new_cpwd')
        # 校验
        if all([old_pwd, new_pwd, new_cpwd]) is False:
            return http.HttpResponseForbidden("缺少必传参数")
        user = request.user
        if user.check_password(old_pwd) is False:
            return render(request, 'user_center_pass.html', {'oringin_pwd_errmsg': '原密码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_pwd):
            return http.HttpResponseForbidden("密码最短8位，最长20位")
        if new_cpwd != new_pwd:
            return http.HttpResponseForbidden("两次密码输入不一致")
        # 修改密码：user.set_password
        user.set_password(new_pwd)
        user.save()
        # 清除登录中状态
        logout(request)
        # 清除cookie中username
        response = redirect('/login/')
        response.delete_cookie('username')
        # 重定向到login界面
        return response


class UserBrowsHistoryView(LoginRequiredView):
    """用户商品浏览记录"""

    def post(self, request):
        # 接收请求体中的sku_id
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        # 检验sku_id是否真实
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("商品不存在")
        # 创建redis连接对象
        redis_conn = get_redis_connection('history')
        # 创建管道
        pl = redis_conn.pipeline()
        # 获取用户并拼接key
        user = request.user
        key = "history_%s" % user.id
        # 去重
        pl.lrem(key, 0, sku_id)
        # 添加到列表开头
        pl.lpush(key, sku_id)
        # 截取列表前5个
        pl.ltrim(key, 0, 4)
        # 执行管道
        pl.execute()
        # 响应
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})

    def get(self, request):
        """获取浏览记录并返回前端展示"""
        # 获取当前登录对象
        user = request.user
        # 创建数据库连接
        redis_conn = get_redis_connection("history")
        # 获取用户所有redis中储存的浏览记录列表
        sku_ids = redis_conn.lrange("history_%s" % user.id, 0, -1)
        # 创建列表保存字典
        sku_list = []
        # 根据浏览记录列表中sku_id获取sku对象模型存入字典
        for sku_id in sku_ids:
            sku_model = SKU.objects.get(id=sku_id)
            sku_list.append({
                "id": sku_model.id,
                "name": sku_model.name,
                "default_image_url": sku_model.default_image.url,
                "price": sku_model.price
            })
        # 响应
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "skus": sku_list})


class UserOrderView(LoginRequiredView, View):
    """订单"""

    def get(self, request, page_num):
        user = request.user
        order_qs = OrderInfo.objects.filter(user_id=user.id)
        order_list = []

        for order_model in order_qs:

            sku_list = []
            sku_qs = OrderGoods.objects.filter(order_id=order_model.order_id)
            for sku_model in sku_qs:
                sku = SKU.objects.get(id=sku_model.sku_id)
                sku_list.append({
                    "name": sku.name,
                    "price": sku_model.price,
                    "count": sku_model.count,
                    "default_image": sku.default_image,
                    "amount": str(sku.price * sku_model.count)

                })

            order_list.append({
                "order_id": order_model.order_id,
                "create_time": order_model.create_time,
                "sku_list": sku_list,
                "total_amount": order_model.total_amount,
                "freight": order_model.freight,
                "pay_method_name": OrderInfo.PAY_METHOD_CHOICES[order_model.pay_method - 1][1],
                "status": order_model.status,
                "status_name": OrderInfo.ORDER_STATUS_CHOICES[order_model.status - 1][1],
                # "pay_method_name": order_model.pay_method,
                # "status_name": order_model.status

            }
            )
        paginator = Paginator(order_list, 5)
        # 获取指定页数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            return http.HttpResponse("当前页面不存在")
        # 获取总页面
        total_page = paginator.num_pages
        # print(order_list)
        context = {
            "page_orders": page_skus,
            "page_num": page_num,
            'total_page': total_page,  # 总页数

        }
        return render(request, "user_center_order.html", context)


class FindPasswordView(View):
    """找回密码"""

    def get(self, request):
        return render(request, "find_password.html")


class CheckInofView(View):
    """第一步"""

    def get(self, request, user_name):
        query_dict = request.GET
        text = query_dict.get("text")
        if all([user_name, text]) is False:
            return http.JsonResponse({"code": RETCODE, "errmsg": "缺少必传参数"})
        uuid = query_dict.get("image_code_id")
        redis_conn = get_redis_connection("verify_code")
        image_code_server = redis_conn.get('img_%s' % uuid)
        image_code_client = query_dict.get('text')
        image_code_server = image_code_server.decode()
        if image_code_server.lower() != image_code_client.lower():
            return http.JsonResponse({"code": RETCODE.IMAGECODEERR, "errmsg": "验证码输入错误"}, status=400)
        if not redis_conn.get("img_%s" % uuid):
            return http.JsonResponse({"code": RETCODE.DBERR, "errmsg": "验证码过期"})

        try:
            if re.match(r'^1[3-9]\d{9}$', user_name):
                # 尝试匹配手机号，成功则将账号输入栏的对应数据库查询项改为mobile
                user = User.objects.get(mobile=user_name)
            else:
                # 否则将账号输入栏的对应数据库查询项设为username
                user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            return http.JsonResponse({"code": RETCODE.USERERR, "errmsg": "账号不存在"}, status=404)

        mobile = user.mobile
        access_token = generate_openid_signature([user_name, mobile])
        mobile = mobile[0:3] + "*" * 4 + mobile[-4:]
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "mobile": mobile, "access_token": access_token})


class SmsCodeSendView(View):
    """发短信"""

    def get(self, request):
        query_dict = request.GET
        access_token = query_dict.get("access_token")
        user_info = check_openid_signature(access_token)
        mobile = user_info[1]
        user_name = user_info[0]

        redis_conn = get_redis_connection('verify_code')
        # 查询数据库中是否有标志
        send_flag = redis_conn.get('sms_flag_%s' % mobile)
        if send_flag:
            return http.JsonResponse({"message": "error"})

        # 生成短信验证码
        sms_code = "%06d" % randint(0, 999999)
        # print(sms_code)
        logger.info(sms_code)
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, 300, sms_code)
        # 设置标志60秒过期，标明该手机号60s内发过一次短信
        pl.setex('sms_flag_%s' % mobile, 60, 1)
        pl.execute()
        send_sms_code.delay(mobile, sms_code)
        return http.JsonResponse({"message": "OK"})


class CheckSmsCodeView(View):
    """第二步,验证短信"""

    def get(self, request, user_name):
        query_dict = request.GET

        sms_code = query_dict.get("sms_code")
        user = User.objects.get(username=user_name)
        mobile = user.mobile
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get("sms_%s" % mobile)
        redis_conn.delete("sms_%s" % mobile)
        if sms_code_server is None:
            return http.HttpResponse("短信验证码过期")
        sms_code_server = sms_code_server.decode()
        if sms_code_server != sms_code:
            return http.HttpResponse("短信验证码输入错误")
        user_id = user.id
        access_token = generate_openid_signature([user_name, mobile])
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "user_id": user_id, "access_token": access_token})


class NewPasswordView(View):
    def post(self, request, user_id):
        json_dict = json.loads(request.body.decode())
        new_pwd = json_dict.get('password')
        new_cpwd = json_dict.get('password2')
        try:
            User.objects.get(id=user_id)
        except User.DoesNotExist:
            return http.HttpResponseForbidden("无此用户")
        access_token = json_dict.get("access_token")
        user_info = check_openid_signature(access_token)
        mobile = user_info[1]
        user_name = user_info[0]
        try:
            User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return http.HttpResponseForbidden("非法请求")
        # 校验
        user = User.objects.get(id=user_id)
        if all([new_pwd, new_cpwd]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_pwd):
            return http.HttpResponseForbidden("密码最短8位，最长20位")
        if new_cpwd != new_pwd:
            return http.HttpResponseForbidden("两次密码输入不一致")
        if authenticate(request, username=user_name, password=new_pwd):
            return http.JsonResponse({"code": RETCODE.PWDERR, "errmsg": "与原密码重复"}, status=400)

        # 修改密码：user.set_password
        user.set_password(new_pwd)
        user.save()

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})

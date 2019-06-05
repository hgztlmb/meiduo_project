from django.shortcuts import render, redirect
from django import http
from django.views import View
import re, json, logging
from django.contrib.auth import login, authenticate, logout, mixins

from goods.models import SKU
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
        return http.JsonResponse({"code":RETCODE.OK,"errmsg":"OK","skus":sku_list})
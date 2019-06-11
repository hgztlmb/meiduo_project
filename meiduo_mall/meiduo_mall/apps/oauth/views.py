import re
from django.shortcuts import render, redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django_redis import get_redis_connection

from carts.utils import merge_cart_cookie_to_redis
from meiduo_mall.utils.response_code import RETCODE
from django import http
import logging
from django.contrib.auth import login

from users.models import User
from .models import OAuthQQUser, OAuthSinaUser
from .utils import generate_openid_signature, check_openid_signature
from meiduo_mall.utils.sinaweibopy3 import *

logger = logging.getLogger('django')


class QQAuthURLView(View):
    """qq登录视图"""

    def get(self, request):
        # 哪里来回哪里去
        next = request.GET.get('next') or '/'
        # 创建qqSDK对象
        auth_qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                          client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=next)
        # 获取qq登录界面url
        login_url = auth_qq.get_qq_url()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})


class QQAuthView(View):
    """qq登录成功回调处理"""

    def get(self, request):
        # 获取code
        code = request.GET.get('code')
        # 校验
        if code is None:
            return http.HttpResponseForbidden("缺少code值")
        # 新建sdk
        auth_qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                          client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI)
        try:
            # 获取access_token
            access_token = auth_qq.get_access_token(code)
            # 获取openid
            openid = auth_qq.get_open_id(access_token)
            # print(openid)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError("QQ的OAuth2.0认证失败")
        # 查询数据库openid是否存在
        try:
            oauth_qq = OAuthQQUser.objects.get(openid=openid)
        # 没有则去绑定
        except OAuthQQUser.DoesNotExist:
            openid = generate_openid_signature(openid)
            return render(request, 'oauth_callback.html', {'openid': openid})
        # 存在则直接登陆成功,获取所关联的用户
        else:
            user = oauth_qq.user
            # 状态保持
            login(request, user)
            # 响应及重定向来源
            next = request.GET.get('state')
            if next == "/orders/settlement/":
                merge_cart_cookie_to_redis(request)
                response = redirect('/carts/')
            else:
                response = redirect(next or '/')

            # cookie中设置username在状态栏中显示登录用户信息
            response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
            response.delete_cookie("carts")
            return response

    def post(self, request):
        """绑定用户"""
        # 获取表单
        query_dict = request.POST
        mobile = query_dict.get('mobile')
        password = query_dict.get('password')
        sms_code = query_dict.get('sms_code')
        openid = query_dict.get('openid')
        # print(openid)
        # 校验
        if all([password, mobile, sms_code]) is False:
            return http.HttpResponse("缺少必要参数")
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponse("请输入8-20位密码")
        if not re.match(r'^1[3456789]\d{9}$', mobile):
            return http.HttpResponse("您输入的手机号格式不正确")
        # 短信验证码
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get("sms_%s" % mobile)
        redis_conn.delete("sms_%s" % mobile)
        if sms_code_server is None:
            return http.HttpResponse("短信验证码过期")
        sms_code_server = sms_code_server.decode()
        if sms_code_server != sms_code:
            return http.HttpResponse("短信验证码输入错误")

        # 解密openid
        openid = check_openid_signature(openid)
        # 判断手机号是否存在，不存在则新建用户
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        else:
            # 校验密码是否正确
            if user.check_password(password) is False:
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        # 绑定用户和openid
        OAuthQQUser.objects.create(
            user=user,
            openid=openid
        )

        # 创建相应对象及重定向
        login(request, user)
        next = request.GET.get('state')
        if next == "/orders/settlement/":
            merge_cart_cookie_to_redis(request)
            response = redirect('/carts/')
        else:
            response = redirect(next or '/')
        # 设置cookie状态栏展示
        response.set_cookie('username', user, max_age=settings.SESSION_COOKIE_AGE)
        response.delete_cookie("carts")
        return response


class WeiboLoginView(View):
    """微博登录"""

    def get(self, request):
        next = request.GET.get('next') or '/'
        # 创建weiboSDK对象
        client = APIClient(app_key=settings.APP_KEY,
                           app_secret=settings.APP_SECRET,
                           redirect_uri=settings.REDIRECT_URL,
                           state=next
                           )
        # 获取weibo登录界面url

        login_url = client.get_authorize_url()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})


class WeiboAuthView(View):
    """weibo登录成功回调处理"""

    def get(self, request):
        # 获取code
        code = request.GET.get('code')
        # 校验
        if code is None:
            return http.HttpResponseForbidden("缺少code值")
        # 新建sdk
        client = APIClient(app_key=settings.APP_KEY,
                           app_secret=settings.APP_SECRET,
                           redirect_uri=settings.REDIRECT_URL
                           )

        try:
            result = client.request_access_token(code)
            access_token = result.access_token
            openid = result.uid
            # print(openid)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError("weibo的OAuth2.0认证失败")
        # 查询数据库openid是否存在
        try:
            oauth_weibo = OAuthSinaUser.objects.get(uid=openid)
        # 没有则去绑定
        except OAuthSinaUser.DoesNotExist:
            openid = generate_openid_signature(openid)
            # print(openid)
            return render(request, 'oauth_callback.html', {'openid': openid})
        # 存在则直接登陆成功,获取所关联的用户
        else:
            user = oauth_weibo.user
            # 状态保持
            login(request, user)
            # 响应及重定向来源
            next = request.GET.get('state')
            if next == "/orders/settlement/":
                merge_cart_cookie_to_redis(request)
                response = redirect('/carts/')
            else:
                response = redirect(next or '/')

            # cookie中设置username在状态栏中显示登录用户信息
            response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
            response.delete_cookie("carts")
            return response

    def post(self, request):
        """绑定用户"""
        # 获取表单
        query_dict = request.POST
        mobile = query_dict.get('mobile')
        password = query_dict.get('password')
        sms_code = query_dict.get('sms_code')
        openid = query_dict.get('openid')
        # print(openid)
        # 校验
        if all([password, mobile, sms_code]) is False:
            return http.HttpResponse("缺少必要参数")
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponse("请输入8-20位密码")
        if not re.match(r'^1[3456789]\d{9}$', mobile):
            return http.HttpResponse("您输入的手机号格式不正确")
        # 短信验证码
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get("sms_%s" % mobile)
        redis_conn.delete("sms_%s" % mobile)
        if sms_code_server is None:
            return http.HttpResponse("短信验证码过期")
        sms_code_server = sms_code_server.decode()
        if sms_code_server != sms_code:
            return http.HttpResponse("短信验证码输入错误")

        # 解密openid
        openid = check_openid_signature(openid)
        # print(openid)
        # 判断手机号是否存在，不存在则新建用户
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        else:
            # 校验密码是否正确
            if user.check_password(password) is False:
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        # 绑定用户和openid
        OAuthSinaUser.objects.create(
            user=user,
            uid=openid
        )

        # 创建相应对象及重定向
        login(request, user)
        next = request.GET.get('state')
        if next == "/orders/settlement/":
            merge_cart_cookie_to_redis(request)
            response = redirect('/carts/')
        else:
            response = redirect(next or '/')
        # 设置cookie状态栏展示
        response.set_cookie('username', user, max_age=settings.SESSION_COOKIE_AGE)
        response.delete_cookie("carts")
        return response

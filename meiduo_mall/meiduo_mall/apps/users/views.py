from django.shortcuts import render, redirect
from django import http
from django.views import View
import re
from django.contrib.auth import login, authenticate
from .models import User
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection
from django.conf import settings


class RegisterView(View):
    # 展示注册界面
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
        sms_code_server = redis_conn.get("sms_%s"%mobile)
        redis_conn.delete("sms_%s" %mobile)
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
        return redirect('/')

# 检查用户名是否重复
class UsernameCountView(View):
    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        response_data = {'count': count, 'code': RETCODE.OK, 'errmsg': 'ok'}
        return http.JsonResponse(response_data)

# 检查手机号是否重复
class MobileCountView(View):
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        response_data = {'count': count, 'code': RETCODE.OK, 'errmsg': 'ok'}
        return http.JsonResponse(response_data)

# 登录界面
class LoginView(View):
    def get(self,request):
        return render(request,'login.html')
    # 获取登录信息
    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 认证用户名和密码（有一个为None即返回None）
        user = authenticate(request,username=username,password=password)
        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})
        # 保持登录状态
        login(request,user)
        # 设置未勾选记住密码时session为关闭浏览器即失效
        if remember != 'on':
            request.session.set_expiry(0)
        # 判断请求来源（url字符串查询）
        next = request.GET.get('next')
        response = redirect(next or '/')
        # 设置cookie
        response.set_cookie('username',username,max_age=settings.SESSION_COOKIE_AGE if remember else None)
        return response


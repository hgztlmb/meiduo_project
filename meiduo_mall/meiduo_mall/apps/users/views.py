from django.shortcuts import render, redirect
from django import http
from django.views import View
import re
from django.contrib.auth import login
from .models import User


class RegisterView(View):
    def get(self, request):

        return render(request, 'register.html')

    def post(self, request):
        query_dict = request.POST
        username = query_dict.get('username')
        password = query_dict.get('password')
        password2 = query_dict.get('password2')
        mobile = query_dict.get('mobile')
        sms_code = query_dict.get('sms_code')
        allow = query_dict.get('allow')

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
        # TODO 短信验证码

        user = User.objects.create_user(username=username, password=password, mobile=mobile)
        login(request, user)

        return redirect('/')

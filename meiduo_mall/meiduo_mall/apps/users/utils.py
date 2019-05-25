from django.contrib.auth.backends import ModelBackend
import re
from .models import User


def get_user_by_account(account):
    """多账号登录"""
    try:
        if re.match(r'^1[3-9]\d{9}$',account):
            # 尝试匹配手机号，成功则将账号输入栏的对应数据库查询项改为mobile
            user = User.objects.get(mobile=account)
        else:
            # 否则将账号输入栏的对应数据库查询项设为username
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    return user


class UsernameMobileAuthBackend(ModelBackend):
    """自定义认证后端"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        # user获取到username或mobile
        user = get_user_by_account(username)
        # 校验账号密码
        if user and user.check_password(password) and user.is_active:
            return user
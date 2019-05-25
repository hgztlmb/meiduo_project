from django.contrib.auth.backends import ModelBackend
import re
from .models import User
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,BadData
from django.conf import settings


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


def generate_email_verify_url(user):
    """邮件url加密"""
    serializer = Serializer(settings.SECRET_KEY,3600*24)
    data = {'user_id':user.id,'email':user.email}
    token = serializer.dumps(data).decode()
    verify_url = settings.EMAIL_VERIFY_URL+'?token='+token
    return verify_url


def check_verify_token(token):
    """邮件url解密"""
    serializer = Serializer(settings.SECRET_KEY,3600*24)
    try :
        data = serializer.loads(token)
    except BadData:
        return None
    else:
        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id=user_id,email=email)
        except User.DoesNotExist:
            return None
        else:
            return user
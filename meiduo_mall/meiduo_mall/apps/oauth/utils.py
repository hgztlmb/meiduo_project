from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings


def generate_openid_signature(openid):
    # 创建加密对象
    serializer = Serializer(settings.SECRET_KEY, 600)
    # 包装为字典
    data = {"openid": openid}
    # 调用dumps方法加密
    openid_sign = serializer.dumps(data)
    # 返回byte类型，解码
    return openid_sign.decode()


def check_openid_signature(openid):
    serializer = Serializer(settings.SECRET_KEY, 600)
    try:
        data = serializer.loads(openid)
    except BadData:
        return None
    return data.get('openid')

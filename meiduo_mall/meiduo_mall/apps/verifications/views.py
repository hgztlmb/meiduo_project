from django.shortcuts import render
from django.views import View
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django import http
from meiduo_mall.utils.response_code import RETCODE
from random import randint
import logging
from celery_tasks.sms.tasks import send_sms_code

logger = logging.getLogger('django')

class ImageCodeView(View):

    def get(self, request, uuid):
        name, text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('img_%s' % uuid, 300, text)
        return http.HttpResponse(image, content_type='image/png')


class SMSCodeView(View):
    def get(self, request, mobile):
        redis_conn = get_redis_connection('verify_code')
        send_flag = redis_conn.get('sms_flag_%s'% mobile)
        if send_flag:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'访问过于频繁'})

        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        if all([image_code_client, uuid]) is False:
            return http.HttpResponse("缺少必要参数")
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            return http.JsonResponse({"code":RETCODE.IMAGECODEERR,"errmsg":"图形验证码已失效"})
        image_code_server = image_code_server.decode()
        if image_code_server.lower() != image_code_client.lower():
            return  http.JsonResponse({"code":RETCODE.IMAGECODEERR,"errmsg":"验证码输入错误"})
        sms_code = "%06d"% randint(0,999999)
        logger.info(sms_code)
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, 300, sms_code)
        pl.setex('sms_flag_%s' % mobile, 60, 1)
        pl.execute()
        send_sms_code.delay(mobile,sms_code)
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'短信验证码发送成功'})


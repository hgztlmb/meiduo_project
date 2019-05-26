from django.shortcuts import render
from django.views import View
from django.core.cache import cache
from .models import Area
from django import http
from meiduo_mall.utils.response_code import RETCODE


class AreasView(View):
    """省市区查询"""
    def get(self, request):
        """获取area_id"""
        area_id = request.GET.get('area_id')
        # 如果area_id为None，则查询数据为省
        if area_id is None:
            # 先从redis中查询，没有再去MySQL中查询
            province_list = cache.get('province_list')
            if province_list is None:
                province_qs = Area.objects.filter(parent=None)
                # 查询对象转换为字典
                province_list = []  # 设置列表储存字典数据
                for province_model in province_qs:
                    province_list.append({
                        'id': province_model.id,
                        'name': province_model.name
                    })
                # 缓存
                cache.set('province_list', province_list, 3600)
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})

        else:
            # 获取指定省或市缓存中的数据
            sub_data = cache.get('sub_area_' + area_id)
            if sub_data is None:
                # 数据库中查询出area_id指定的省或市
                try:
                    parent_model = Area.objects.get(id=area_id)
                except Area.DoesNotExist:
                    return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': 'area_id不存在'})
                # 根据指定省市获取所有下级市或区数据
                sub_qs = parent_model.subs.all()
                # 定义列表包装数据
                sub_list = []
                # 循环遍历数据并转换为字典加入列表
                for sub_model in sub_qs:
                    sub_list.append({
                        'id': sub_model.id,
                        'name': sub_model.name
                    })
                # 包装数据
                sub_data = {
                    'id': parent_model.id,
                    'name': parent_model.name,
                    'subs': sub_list
                }
                # 缓存数据
                cache.set('sub_area_' + area_id, sub_data, 3600)
                # 响应
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})

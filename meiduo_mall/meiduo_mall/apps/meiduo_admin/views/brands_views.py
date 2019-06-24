from fdfs_client.client import Fdfs_client
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from meiduo_admin.serializers.brand_serializers import *
from meiduo_admin.pages import UserPageNum


class BrandAdminView(ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandAdminSerializer
    pagination_class = UserPageNum

    # def create(self, request, *args, **kwargs):
    #     # 创建FastDFS连接对象
    #     client = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")
    #     # 获取前端传递的image文件
    #     data = request.FILES.get('logo')
    #     # 上传图片到fastDFS
    #     res = client.upload_by_buffer(data.read())
    #     # 判断是否上传成功
    #     if res['Status'] != 'Upload successed.':
    #         return Response(status=403)
    #     # 获取上传后的路径
    #     logo_url = res['Remote file_id']
    #
    #     name = request.data.get("name")
    #     first_letter = request.data.get("first_letter")[0]
    #     # 保存图片
    #     img = Brand.objects.create(name=name, first_letter=first_letter, logo=logo_url)
    #     # 返回结果
    #     return Response(
    #         {
    #             'id': img.id,
    #             'name': name,
    #             'first_letter': first_letter,
    #             'logo': img.logo.url
    #         },
    #         status=201  # 前端需要接受201状态
    #     )
    #
    # def update(self, request, *args, **kwargs):
    #
    #     # 创建FastDFS连接对象
    #     client = Fdfs_client("meiduo_mall/utils/fastdfds/client.conf")
    #     # 获取前端传递的image文件
    #     # try:
    #     data = request.FILES.get('logo')
    #     # 上传图片到fastDFS
    #
    #     res = client.upload_by_buffer(data.read())
    #     # 判断是否上传成功
    #     if res['Status'] != 'Upload successed.':
    #         return Response(status=403)
    #     # 获取上传后的路径
    #     logo_url = res['Remote file_id']
    #
    #     # 查询图片对象
    #     name = request.data.get("name")
    #     first_letter = request.data.get("first_letter")[0]
    #     img = Brand.objects.get(id=kwargs['pk'])
    #     # 更新图片
    #     img.name = name
    #     img.first_letter = first_letter
    #     img.logo = logo_url
    #     img.save()
    #     # 返回结果
    #     return Response(
    #         {
    #             'id': img.id,
    #             'name': name,
    #             'first_letter': first_letter,
    #             'logo': img.logo.url
    #         },
    #         status=201  # 前端需要接受201状态码
    #         )
        # except:
        #     partial = kwargs.pop('partial', False)
        #     instance = self.get_object()
        #     serializer = self.get_serializer(instance, data=request.data, partial=partial)
        #     serializer.is_valid(raise_exception=True)
        #     self.perform_update(serializer)
        #     if getattr(instance, '_prefetched_objects_cache', None):
        #         # If 'prefetch_related' has been applied to a queryset, we need to
        #         # forcibly invalidate the prefetch cache on the instance.
        #         instance._prefetched_objects_cache = {}
        #
        #     return Response(serializer.data)
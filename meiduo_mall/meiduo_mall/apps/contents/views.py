from django.shortcuts import render
from django.views import View
from goods.models import GoodsChannel
from contents.models import ContentCategory
from .utils import get_categories


class IndexView(View):
    def get(self, request):
        # 定义一个字典categories包装所有数据
        # categories = {}
        # # 查询出所有商品频道数据并按照group_id(组),sequence(组内顺序)进行排序
        # good_channel_qs = GoodsChannel.objects.order_by('group_id', 'sequence')
        # # 遍历查询集（商品频道数据）
        # for channel in good_channel_qs:
        #     # 获取当前商品group_id
        #     group_id = channel.group_id
        #     # 判断组别（group_id）是否存在字典中
        #     if channel.group_id not in categories:
        #         # 不存在则添加一个新的数据格式：{group_id:{“channels":[],"sub_cats":[]}}
        #         categories[group_id] = {"channels": [], "sub_cats": []}
        #     # 通过频道获取一级商品数据模型category
        #     cat1 = channel.category
        #     # 把频道的url赋给cat1
        #     cat1.url = channel.url
        #     # 将一级商品数据加入字典channels中
        #     categories[group_id]["channels"].append(cat1)
        #     # 获取当前一级下二级商品数据查询集
        #     cat2_qs = cat1.subs.all()
        #     # 遍历二级数据查询集
        #     for cat2 in cat2_qs:
        #         # 获取三级数据查询集
        #         cat3_qs = cat2.subs.all()
        #         # 将当前二级数据下的三级数据查询集保存到二级数据的sub_cats属性中
        #         cat2.sub_cats = cat3_qs
        #         # 将二级数据加入字典sub_cats中
        #         categories[group_id]["sub_cats"].append(cat2)

        # 首页广告
        # 建立字典保存广告数据
        contents = {}
        # 获取广告类别查询集
        contents_qs = ContentCategory.objects.all()
        # 遍历广告类型查询集
        for cat in contents_qs:
            # 构建广告数据格式
            contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        context = {
            "categories": get_categories(),
            "contents": contents
        }
        return render(request, 'index.html', context)

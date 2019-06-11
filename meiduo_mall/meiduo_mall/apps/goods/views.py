from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django import http
from contents.utils import get_categories
from orders.models import OrderGoods, OrderInfo
from users.models import User
from .models import GoodsCategory, SKU, GoodsVisitCount
from .utils import get_breadcrumb
from django.core.paginator import Paginator, EmptyPage
from meiduo_mall.utils.response_code import RETCODE


class ListViews(View):
    """商品列表页面"""

    def get(self, request, category_id, page_num):
        # 获取商品类别中商品信息
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponse("商品类别不存在")
        # 获取前端传递的排序信息
        sort = request.GET.get('sort')
        if sort == 'price':
            sort_field = 'price'
        elif sort == 'hot':
            sort_field = '-sales'
        else:
            sort = 'default'
            sort_field = '-create_time'

        # 获取当前三级类别中所有上架的商品sku信息
        sku_qs = SKU.objects.filter(category=category, is_launched=True).order_by(sort_field)
        # 创建分页对象，设定每页最多显示几个
        paginator = Paginator(sku_qs, 5)
        # 获取指定页数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            return http.HttpResponse("当前页面不存在")
        # 获取总页面
        total_page = paginator.num_pages

        context = {
            "categories": get_categories(),
            "category": category,
            "page_num": page_num,
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sort': sort,  # 排序字段

            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数

        }

        return render(request, 'list.html', context)


class HotSaleView(View):
    """热销商品排行"""

    def get(self, request, category_id):
        # 获取当前类别中的商品信息
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponse("商品类别不存在")

        # 将商品按销量倒序
        skus_qs = SKU.objects.filter(category=category, is_launched=True).order_by('-sales')[:2]
        # 包装为字典
        hot_skus = []
        for sku in skus_qs:
            hot_skus.append({
                "id": sku.id,
                "name": sku.name,
                "price": sku.price,
                "default_image_url": sku.default_image.url
            })
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "hot_skus": hot_skus})


class DetailView(View):
    """商品详情页面"""

    def get(self, request, sku_id):
        # 获取选择的sku数据
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, "404.html")
        category = sku.category
        spu = sku.spu
        """1.准备当前商品的规格选项列表 [8, 11]"""
        # 获取出当前正显示的sku商品的规格选项id列表
        current_sku_spec_qs = sku.specs.order_by('spec_id')
        current_sku_option_ids = []  # [1, 4, 7]
        for current_sku_spec in current_sku_spec_qs:
            current_sku_option_ids.append(current_sku_spec.option_id)

        """2.构造规格选择仓库
        {(8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}
        """
        # 构造规格选择仓库
        temp_sku_qs = spu.sku_set.all()  # 获取当前spu下的所有sku
        # 选项仓库大字典
        spec_sku_map = {}  # {(1, 4, 7): 1, (8, 11): 3, (8, 12): 4, (9, 11): 5, (9, 12): 6, (10, 11): 7, (10, 12): 8}
        for temp_sku in temp_sku_qs:
            # 查询每一个sku的规格数据
            temp_spec_qs = temp_sku.specs.order_by('spec_id')
            temp_sku_option_ids = []  # 用来包装每个sku的选项值
            for temp_spec in temp_spec_qs:
                temp_sku_option_ids.append(temp_spec.option_id)
            spec_sku_map[tuple(temp_sku_option_ids)] = temp_sku.id

        """3.组合 并找到sku_id 绑定"""
        spu_spec_qs = spu.specs.order_by('id')  # 获取当前spu中的所有规格

        for index, spec in enumerate(spu_spec_qs):  # 遍历当前所有的规格
            spec_option_qs = spec.options.all()  # 获取当前规格中的所有选项
            temp_option_ids = current_sku_option_ids[:]  # 复制一个新的当前显示商品的规格选项列表
            for option in spec_option_qs:  # 遍历当前规格下的所有选项
                temp_option_ids[index] = option.id  # [1, 4, 7]
                option.sku_id = spec_sku_map.get(tuple(temp_option_ids))  # 给每个选项对象绑定下他sku_id属性

            spec.spec_options = spec_option_qs  # 把规格下的所有选项绑定到规格对象的spec_options属性上

        # 包装数据
        context = {
            "categories": get_categories(),
            "category": category,
            "sku": sku,
            "breadcrumb": get_breadcrumb(category),
            "spu": spu,
            "spec_qs": spu_spec_qs,

        }
        return render(request, "detail.html", context)


class DetailVisitView(View):
    """记录访问量"""

    def post(self, request, category_id):
        # 检验category_id是否存在
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden("商品不存在")
        # 获取当前日期
        date = timezone.now()
        # print(date)
        # 检查访问category_id在数据库中是否有当前日期的记录
        try:
            goods_visit = GoodsVisitCount.objects.get(category=category, date=date)
        except GoodsVisitCount.DoesNotExist:
            # 没有则说明是今天第一次访问,新建一个记录
            goods_visit = GoodsVisitCount(category_id=category_id)
        # 存在则count+=1
        goods_visit.count += 1
        goods_visit.save()
        # 响应
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK"})


class ShowCommentsView(View):
    """评论展示"""

    def get(self, request, sku_id):

        comments_qs = OrderGoods.objects.filter(sku_id=sku_id, is_commented=True)
        comment_list = []
        for order_model in comments_qs:
            user_name = order_model.order.user.username
            if order_model.is_anonymous:
                user_name = user_name[0:2] + "***" + user_name[-2:-1]
            comment_list.append({
                "comment": order_model.comment,
                "username": user_name,
                "score": order_model.score,

            })

        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "OK", "comment_list": comment_list})

from django_redis import get_redis_connection
import pickle, base64


def merge_cart_cookie_to_redis(request):
    """购物车合并"""
    # 获取cookie
    carts_str = request.COOKIES.get("carts")
    # 判断是否有商品,没有则提前返回
    if not carts_str:
        return
    # cookie字符串转为字典
    carts_dict = pickle.loads(base64.b64decode(carts_str.encode()))
    # 创建redis连接对象
    user = request.user
    redis_conn = get_redis_connection("carts")
    # cookie加入redis
    pl = redis_conn.pipeline()
    for sku_id, sku_dict in carts_dict.items():
        pl.hset("carts_%s" % user.id, sku_id, sku_dict['count'])
        if carts_dict[sku_id]["selected"]:
            pl.sadd("selected_%s" % user.id, sku_id)
        else:
            pl.srem("selected_%s" % user.id, sku_id)
    pl.execute()
    # 删除cookie

def get_breadcrumb(category):
    """面包屑导航数据包装"""
    # 根据传入的三级数据获取一级数据
    cat1 = category.parent.parent
    # 传入一级数据url
    cat1.url = cat1.goodschannel_set.all()[0].url
    # 包装数据
    breadcrumb = {
        'cat1': cat1,
        'cat2': category.parent,
        'cat3': category
    }
    return breadcrumb

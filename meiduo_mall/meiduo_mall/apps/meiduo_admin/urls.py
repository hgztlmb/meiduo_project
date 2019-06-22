from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import SimpleRouter

from meiduo_admin.views.spu_info_view import *
from .views.sku_info_views import *
from .views.user_admin_views import UserAdminView
from .views.user_home_views import UserHomeView

urlpatterns = [

    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^skus/categories/$', CategoryInfoView.as_view()),
    url(r'^goods/simple/$', SPUInfoView.as_view()),
    url(r'^goods/(?P<pk>\d+)/specs/$', SPUSpecView.as_view()),
    url(r'^goods/channel/categories/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/channel/categories/(?P<pk>\d+)/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/brands/simple/$', BrandView.as_view()),


]
routers = SimpleRouter()
routers.register(prefix="statistical", viewset=UserHomeView, base_name="UserHomeView")
routers.register(prefix='users',viewset=UserAdminView,base_name="UserAdminView")
routers.register(prefix='skus',viewset=SKUInfoView,base_name="SKUInfoView")
routers.register(prefix='goods',viewset=SPUView,base_name="SPUView")

urlpatterns += routers.urls


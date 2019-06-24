from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import SimpleRouter

from .views.brands_views import BrandAdminView
from .views.spu_info_view import *
from .views.sku_info_views import *
from .views.user_admin_views import UserAdminView
from .views.user_home_views import UserHomeView
from .views.specs_views import*
from .views.channel_views import *
from .views.image_views import *

urlpatterns = [

    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^skus/categories/$', CategoryInfoView.as_view()),
    url(r'^goods/simple/$', SPUInfoView.as_view()),
    url(r'^goods/(?P<pk>\d+)/specs/$', SPUSpecView.as_view()),
    url(r'^goods/channel/categories/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/channel/categories/(?P<pk>\d+)/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/brands/simple/$', BrandView.as_view({'get': 'list'})),
    url(r'^goods/specs/simple/$', SPUSpecView.as_view()),
    url(r'^goods/categories/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/categories/(?P<pk>\d+)/$', CategoryView.as_view({'get': 'list'})),
    url(r'^goods/channel_types/$', ChannelGroupView.as_view({'get': 'list'})),
    url(r'^skus/simple/$', ImageViewSet.as_view({'get': 'simple'})),


]
routers = SimpleRouter()
routers.register(prefix="statistical", viewset=UserHomeView, base_name="UserHomeView")
routers.register(prefix='users',viewset=UserAdminView,base_name="UserAdminView")
routers.register(prefix='skus/images',viewset=ImageViewSet,base_name="ImageViewSet")
routers.register(prefix='skus',viewset=SKUInfoView,base_name="SKUInfoView")
routers.register(prefix='specs/options',viewset=SpecsOptionsView,base_name="SpecsOptionsView")
routers.register(prefix='goods/channels',viewset=ChannelView,base_name="ChannelView")
routers.register(prefix='goods/specs',viewset=SpecsInfoView,base_name="SpecsInfoView")
routers.register(prefix='goods/brands',viewset=BrandAdminView,base_name="BrandAdminView")
routers.register(prefix='goods',viewset=SPUView,base_name="SPUView")

urlpatterns += routers.urls


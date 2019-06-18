from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import SimpleRouter
from .views.user_admin_info import UserAdminInfo


urlpatterns = [

    url(r'^authorizations/$',obtain_jwt_token)
]
routers = SimpleRouter()
routers.register(prefix="statistical",viewset=UserAdminInfo,base_name="UserAdminInfo")
urlpatterns += routers.urls
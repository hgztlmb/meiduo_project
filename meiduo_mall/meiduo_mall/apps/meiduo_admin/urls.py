from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import SimpleRouter

from .views.user_admin_views import UserAdminView
from .views.user_home_views import UserHomeView


urlpatterns = [

    url(r'^authorizations/$',obtain_jwt_token),
    url(r'^users/$',UserAdminView.as_view())

]
routers1 = SimpleRouter()
routers1.register(prefix="statistical",viewset=UserHomeView,base_name="UserHomeView")
urlpatterns += routers1.urls

# routers2 = SimpleRouter()
# routers2.register(prefix="users",viewset=UserAdminView,base_name="UserAdminView")
# urlpatterns += routers2.urls
from django.conf.urls import url
from apps.user.views import RegisterView,ActiveView,LoginView,User_Center_Info,User_Center_Order,User_Center_Site,LoginOut
from django.contrib.auth.decorators import login_required

urlpatterns = [
        # url(r'^register$',views.register,name='register'),
        # url(r'^register_handle$',views.register_handle,name='register_handle')
    url(r'^register$',RegisterView.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    url(r'^login$',LoginView.as_view(),name='login'),
    # 用户中心类
    url(r'^$',User_Center_Info.as_view(),name='user'),
    url(r'^order/(\d+)$',User_Center_Order.as_view(),name='order'),
    url(r'^address$',User_Center_Site.as_view(),name='address'),
    url(r'^loginout$',LoginOut.as_view(),name='logout')
]

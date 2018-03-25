from django.conf.urls import url
from apps.goods import views
from apps.goods.views import IndexView,DetailView,ListDateView


urlpatterns = [
        url(r'^index$', IndexView.as_view(), name='index'),
        url(r'detail/(\d+)',DetailView.as_view(),name='detail'),
        url(r'list/(\d+)/(\d+)',ListDateView.as_view(),name='list'),


]
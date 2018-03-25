from apps.order.views import PlaceOrderView,CommitView,AlipayView,OrderCheckView,CommentView
from django.conf.urls import url
urlpatterns = [
        url(r'^place$', PlaceOrderView.as_view(), name='place'),
        url(r'^commit$',CommitView.as_view(),name='commit'),
        url(r'^pay$',AlipayView.as_view(),name='pay'),
        url(r'^check$',OrderCheckView.as_view(),name='check'),
        url(r'^comment/(\d+)$',CommentView.as_view(),name='comment')

]
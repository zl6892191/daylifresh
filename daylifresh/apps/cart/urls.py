from django.conf.urls import url
from apps.cart.views import CartAddView,CartView,CartUpdateView,CartDeleteView


urlpatterns = [
        url(r'^add$',CartAddView.as_view(),name='add'),
        url(r'^$',CartView.as_view(),name='show'),
        url(r'^update$',CartUpdateView.as_view(),name='update'),
        url(r'^delete$',CartDeleteView.as_view(),name='delete')
]
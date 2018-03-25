from django.views.generic import View
from django.contrib.auth.decorators import login_required

class LoginReuiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return login_required(view)

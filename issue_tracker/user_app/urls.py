from django.urls import path
from .views import UserViewSet

urlpatterns = [
    path('signup/', UserViewSet.as_view({'post': 'signup'}), name='user-signup'),
    path('signin/', UserViewSet.as_view({'post': 'signin'}), name='user-signin'),
]
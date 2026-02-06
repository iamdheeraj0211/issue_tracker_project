from django.urls import path
from .views import LabelViewSet

urlpatterns = [
    path('labels/', LabelViewSet.as_view({'get': 'list', 'post': 'create'}), name='label-list'),
    path('labels/<int:pk>/', LabelViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='label-detail'),
]

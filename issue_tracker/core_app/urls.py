from django.urls import path
from .views import LabelViewSet, IssueViewSet

urlpatterns = [
    # Label endpoints
    path('labels/', LabelViewSet.as_view({'get': 'list', 'post': 'create'}), name='label-list'),
    path('labels/<int:pk>/', LabelViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='label-detail'),
]


# Issue endpoints
urlpatterns += [
    path('issues', IssueViewSet.as_view({'get': 'list', 'post': 'create'}), name='issue-list'),
    path('issues/<int:pk>', IssueViewSet.as_view({'put': 'update', 'delete': 'destroy' ,'get':'retrieve'}), name='issue-detail'),

    path('issues/<int:pk>/comments', IssueViewSet.as_view({'post': 'add_comment'}), name='issue-comment'),
    path('issues/<int:pk>/labels', IssueViewSet.as_view({'put': 'replace_labels'}), name='issue-label'),
    path('issues/bulk-status', IssueViewSet.as_view({'post': 'bulk_status'}), name='issue-bulk-status-update'),
]

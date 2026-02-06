from rest_framework import viewsets ,status
from .models import Issue, Comment, Label
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from .helpers import CustomCursorPagination
# Create your views here.
class LabelViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    pagination_class = CustomCursorPagination
    
    def list(self, request):
        id=request.query_params.get('id')
        keyword=request.query_params.get('keyword')
        labels = Label.objects.filter(is_deleted=False)
        if id:
            labels=labels.filter(id=id)
        if keyword:
            labels=labels.filter(name__icontains=keyword)
        paginator = self.pagination_class()
        labels = labels.values('id', 'name')
        paginated_labels = paginator.paginate_queryset(labels, request)
        return paginator.get_paginated_response(paginated_labels)

    def create(self, request):
        name = request.data.get('name')
        if not name:
            return Response({
                'success': False,
                'message': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        name =name.capitalize()
        if Label.objects.filter(name__iexact=name).exists():
            return Response({
                'success': False,
                'message': 'Label already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        label = Label.objects.create(name=name)
        return Response({
            'success': True,
            'message': 'Label created successfully',
            'data': {
                'id': label.id,
                'name': label.name
            }
        }, status=status.HTTP_201_CREATED)


    def destroy(self, request, pk=None):
        label = Label.objects.filter(id=pk, is_deleted=False).first()
        if not label:
            return Response({
                'success': False,
                'message': 'Label not found'
            }, status=status.HTTP_404_NOT_FOUND)
        label.is_deleted = True
        label.save()
        return Response({
            'success': True,
            'message': 'Label deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk=None):
        label = Label.objects.filter(id=pk, is_deleted=False).first()
        if not label:
            return Response({
                'success': False,
                'message': 'Label not found'
            }, status=status.HTTP_404_NOT_FOUND)
        name = request.data.get('name')
        if not name:
            return Response({
                'success': False,
                'message': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        name = name.capitalize()
        if Label.objects.filter(name__iexact=name).exists():
            return Response({
                'success': False,
                'message': 'Label already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        label.name = name
        label.save()
        return Response({
            'success': True,
            'message': 'Label updated successfully',
            'data': {
                'id': label.id,
                'name': label.name
            }
        }, status=status.HTTP_200_OK)

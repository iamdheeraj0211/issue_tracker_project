from rest_framework import viewsets ,status
from .models import Issue, Comment, Label ,User
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from .helpers import CustomCursorPagination
from django.db import transaction

class IssueViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    pagination_class = CustomCursorPagination

    def list(self, request):
        id=request.query_params.get('id')
        keyword=request.query_params.get('keyword')
        queryset = Issue.objects.filter(is_deleted=False)
        if id:
            queryset = queryset.filter(id=id)
        if keyword:
            queryset = queryset.filter(title__icontains=keyword) | queryset.filter(description__icontains=keyword)

        paginator = self.pagination_class()
        queryset = queryset.values('id', 'title','description','assignee__username')
        paginated_issues = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(paginated_issues)

    def create(self, request):
        title = request.data.pop('title')
        description = request.data.pop('description')
        assignee_id = request.data.pop('assignee_id',None)
        label_ids = request.data.pop('labels', [])
        is_deleted = request.data.pop('is_deleted', False)
        if not title or not description:
            return Response(
                {"error": "Please provide title, description"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if assignee_id:
            if not User.objects.filter(id=assignee_id).exists():
                return Response(
                    {"error": f"Assignee with id {assignee_id} does not exist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        if label_ids:
            exsitng_label_ids=Label.objects.filter(is_deleted=False).values_list('id',flat=True)
            not_existing_label_ids=[]
            for label_id in label_ids:
                if label_id not in exsitng_label_ids:
                    not_existing_label_ids.append(label_id)
            if not_existing_label_ids:
                return Response(
                    {"error": f"lable with ids {not_existing_label_ids} does not exist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
       
        issue = Issue.objects.create(
            title=title,
            description=description,
            assignee_id=assignee_id,
            **request.data,
            created_by=request.user,
            updated_by=request.user,
        )
        if label_ids:
            issue.labels.set(label_ids)
        return Response(
            {"message": "Issue created successfully", "issue_id": issue.id}, 
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        try:
            issue = Issue.objects.filter(id=pk, is_deleted=False)

            if not issue.exists():
                return Response(
                    {"error": "Issue not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            comments = list(Comment.objects.filter(issue_id=pk,is_deleted=False).order_by('-id').values('id','comment','created_at','updated_at','author__username'))

            issue = Issue.objects.select_related('assignee').prefetch_related('labels').get(id=pk)
            
            # Clean data structure without duplicates
            data = {
                "id": issue.id,
                "title": issue.title,
                "description": issue.description,
                "status": issue.status,
                "assignee":{
                    "id": issue.assignee.id,
                    "username": issue.assignee.username,
                } if issue.assignee else None,
                "labels": list(issue.labels.values('id','name').order_by('-id')) if issue.labels.exists() else None,
                'comments': comments,
            }
            return Response({"issue": data})
        except Exception as e:
            return Response({"error": str(e)}, status=404)


    def update(self, request, pk=None):
        pass
    def destroy(self, request, pk=None):
        pass

    def add_comment(self, request, pk=None):
        comment = request.data.pop('comment')
        if not comment:
            return Response(
                {"error": "Please provide comment"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        issue=Issue.objects.filter(id=pk, is_deleted=False)
        if not issue.exists():
            return Response(
                {"error": "Issue not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        comment_obj=Comment.objects.create(
            issue_id=pk,
            comment=comment,
            author=request.user,
        )
        return Response(
            {"message": "Comment added successfully",
            "data":{
                "id": comment_obj.id,
                "issue_id": pk,
                "comment": comment,
                "created_at": comment_obj.created_at,
                'author': comment_obj.author.username if comment_obj.author else None,
            }}, 
            status=status.HTTP_201_CREATED
        )

    def replace_labels(self, request, pk=None):
        label_ids = request.data.pop('labels', [])
        if not label_ids:
            return Response(
                {"error": "Please provide labels"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        exsitng_label_ids=Label.objects.filter(is_deleted=False).values_list('id',flat=True)
        not_existing_label_ids=[]
        for label_id in label_ids:
            if label_id not in exsitng_label_ids:
                not_existing_label_ids.append(label_id)
        if not_existing_label_ids:
            return Response(
                {"error": f"lable with ids {not_existing_label_ids} does not exist"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        issue=Issue.objects.filter(id=pk, is_deleted=False)
        if not issue.exists():
            return Response(
                {"error": "Issue not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        issue=issue.first()
        issue.labels.set(label_ids)
        return Response(
            {"message": "Labels replaced successfully", "issue_id": issue.id}, 
            status=status.HTTP_200_OK
        )

    def bulk_status(self, request):
        try:
            ids = request.data.get('ids', [])
            new_status = request.data.get('status')

            if not ids or not new_status:
                return Response({"error": "Please provide 'ids' list and 'status'"}, status=status.HTTP_400_BAD_REQUEST)

            valid_statuses = [choice[0] for choice in Issue.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response({"error": "Invalid status value choose from "+",".join(valid_statuses)}, status=status.HTTP_400_BAD_REQUEST)

            existing_qs=Issue.objects.filter(is_deleted=False)
            existing_ids = existing_qs.values_list('id',flat=True)
            not_existing_ids=[]
            for id in ids:
                if id not in existing_ids:
                    not_existing_ids.append(id)
            if not_existing_ids:
                return Response(
                    {"error": f"issues with ids {not_existing_ids} does not exist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )   

            # 3. Transactional Block
            with transaction.atomic():
                # Filter issues that exist and are in the ID list
                to_update_qs = existing_qs.filter(id__in=ids)
                updated_count=to_update_qs.count()
                to_update_qs.update(status=new_status)
                
                return Response({
                    "message": f"Successfully updated {updated_count} issues to {new_status}"
                }, status=200)

        except Exception as e:
            return Response({"error": f"Transaction failed: {str(e)}"}, status=500)

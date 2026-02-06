from rest_framework import viewsets ,status
from .models import Issue, Comment, Label ,User
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response

from .helpers import CustomCursorPagination
from django.db import transaction
from django.db.models import Count, F
import pandas as pd
from django.utils import timezone

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
                'version': issue.version,
            }
            return Response({"issue": data})
        except Exception as e:
            return Response({"error": str(e)}, status=404)


    def update(self, request, pk=None):
        data=request.data.copy()
        user_version = data.pop('version', None)
        is_deleted = data.pop('is_deleted', False)
        if not user_version:
            return Response(
                {"error": "Please provide version"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        label_update=False
        if 'labels' in data:
            label_ids = data.pop('labels', [])
            label_update=True
       
        assignee_id = data.pop('assignee_id', None)
        if assignee_id:
            if not User.objects.filter(id=assignee_id).exists():
                return Response(
                    {"error": f"Assignee with id {assignee_id} does not exist"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            data['assignee_id']=assignee_id
        

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
        with transaction.atomic():
            updated_rows = (
                Issue.objects
                .filter(id=pk, is_deleted=False, version=user_version)
                .update(
                    **data,
                    version=    F("version") + 1,
                    updated_by=request.user,
                )
            )
            # print(updated_rows,"updated_rows")
            if updated_rows == 0:
                return Response(
                    {"error": "Conflict: issue already updated by another user"},
                    status=status.HTTP_409_CONFLICT,
                )
            issue = Issue.objects.get(id=pk)
            if label_update:
                issue.labels.set(label_ids)

        return Response(
            {"message": "Issue updated successfully", "issue_id": issue.id},
            status=status.HTTP_200_OK,
        )


    def destroy(self, request, pk=None):
        issue=Issue.objects.filter(id=pk, is_deleted=False)
        if not issue.exists():
            return Response(
                {"error": "Issue not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        issue.update(
            is_deleted=True,
            updated_by=request.user,
        )
        return Response(
            {"message": f"Issue with id {pk} deleted successfully"}, 
            status=status.HTTP_200_OK
        )

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

            with transaction.atomic():
                to_update_qs = existing_qs.filter(id__in=ids)
                updated_count=to_update_qs.count()
                if new_status=="resolved":
                    to_update_qs.update(status=new_status,resolved_at=timezone.now())
                else:
                    to_update_qs.update(status=new_status)
                
                return Response({
                    "message": f"Successfully updated {updated_count} issues to {new_status}"
                }, status=200)



class IssueImportandReportView(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic()
    def import_csv(self, request):
        try:
            csv_file = request.FILES.get('file')
            if not csv_file:
                return Response(
                    {"error": "Please provide a CSV or Excel file"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_type=csv_file.name.split('.')[-1]
            if file_type not in ['csv','xlsx']:
                return Response(
                    {"error": "Please provide a CSV or Excel file"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if file_type=='csv':
                df = pd.read_csv(csv_file)
            else:
                df = pd.read_excel(csv_file)
            required_columns=['title','description','status','labels']
            if not all(col in df.columns for col in required_columns):
                return Response(
                    {"error": f"Please provide all required columns {required_columns}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            status_choices=[choice[0] for choice in Issue.STATUS_CHOICES]

            label_qs=Label.objects.filter(is_deleted=False).values('id','name')
            label_dict_map={item['name'].lower():item['id'] for item in label_qs}

            user_qs=User.objects.filter(is_active=True).values('id','username')
            user_dict_map={item['username'].lower():item['id'] for item in user_qs} 
            error_Details=[]
            objects_to_create=[]
            if len(df)==0:
                return Response(
                    {"error": "Please provide data in the file"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            for index, row in df.iterrows():
                title = row.get('title')
                if not title or pd.isna(title):
                    error_Details.append({"error": f"Please provide title for row {index}"})
                    continue
                
                description = row.get('description')
                
                if not description or pd.isna(description):
                    error_Details.append({"error": f"Please provide description for row {index}"})
                    continue
            
                new_status = row.get('status')  
                if not new_status or pd.isna(new_status) or new_status not in status_choices:
                    error_Details.append({"error": f"Please provide valid status for row {index}"})
                    continue
                labels = row.get('labels')
                if not labels or pd.isna(labels):
                    return Response(
                        {"error": f"Please provide labels for row {index}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    label_names=labels.split(',')
                    label_ids=[]    
                    for label_name in label_names:
                        label_name=label_name.strip().lower()
                        if label_name not in label_dict_map:
                            error_Details.append({"error": f"Please provide valid label name {label_name} for row {index}"})
                            continue
                        label_ids.append(label_dict_map[label_name])
                assignee = row.get('assignee')
                if not assignee or pd.isna(assignee):
                    assignee_id=None
                else:
                    assignee=str(assignee)
                    assignee=assignee.strip().lower()
                    if assignee not in user_dict_map:
                        error_Details.append({"error": f"Please provide valid assignee name {assignee} for row {index}"})
                        continue
                    assignee_id=user_dict_map[assignee] 

                issue_obj = Issue(
                    title=title,
                    description=description,
                    status=new_status,
                    assignee_id=assignee_id,
                    created_by=request.user,
                    updated_by=request.user
                )
                objects_to_create.append((issue_obj, label_ids))

            if error_Details:
                return Response(
                    {"message":"Please check the error_details to fix the errors in file before importing",    
                    "error_details": error_Details}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            if objects_to_create:
                issues_only = [item[0] for item in objects_to_create]
                created_issues = Issue.objects.bulk_create(issues_only)
                
                for i, issue in enumerate(created_issues):
                    original_labels = objects_to_create[i][1]
                    if original_labels:
                        issue.labels.set(original_labels)

            return Response({
                "message": f"Successfully imported {len(objects_to_create)} issues and error while importing {len(error_Details)} issues",
                "error_details": error_Details
            }, status=201)
        
        except Exception as e:
            return Response(
                {"error": f"Error while importing issues: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def top_assignee(self,request):
        try:
            top_assignee_qs=Issue.objects.filter(assignee__isnull=False).values('assignee__username').annotate(
                count=Count('assignee__username')
            ).order_by('-count')[:10]
            top_assignee_list=[{'assignee':item['assignee__username'],'count':item['count']} for item in top_assignee_qs]   
            return Response({
                "message": "Successfully fetched top 10 assignees",
                "top_assignees": top_assignee_list
            }, status=200)
        except Exception as e:
            return Response(
                {"error": f"Error while fetching top assignees: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_average_time(self,request):
        try:
            average_time_qs=Issue.objects.filter(status__in=['closed','resolved'],resolved_at__isnull=False).values('created_at','resolved_at')
            # print(average_time_qs.count())
            df=pd.DataFrame(list(average_time_qs))
            df['created_at']=pd.to_datetime(df['created_at'])
            df['resolved_at']=pd.to_datetime(df['resolved_at'])
            df['time_taken']=(df['resolved_at']-df['created_at']).dt.total_seconds()/60 #minutes
            average_time=df['time_taken'].mean()
            return Response({
                "message": "Successfully fetched average time",
                "average_time": f"{round(average_time,2)} minutes"
            }, status=200)
        except Exception as e:
            return Response(
                {"error": f"Error while fetching average time: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


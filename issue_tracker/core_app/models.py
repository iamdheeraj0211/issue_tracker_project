from django.db import models
from django.contrib.auth.models import User

class Label(models.Model):
    name = models.CharField(max_length=50, unique=True)

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'labels'

class Issue(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_issues')
    labels = models.ManyToManyField(Label, related_name='issues')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_issues')
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'issues'
      

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_comments') 
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_comments')
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'comments'
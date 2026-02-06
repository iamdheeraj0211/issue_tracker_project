from django.db import models
from django.contrib.auth.models import User

class Label(models.Model):
    name = models.CharField(max_length=50, unique=True)

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'labels'

    def __str__(self):
        return f"{self.id} {self.name}"

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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues' ,null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_issues' ,null=True, blank=True)
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    version = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.id} {self.title} {self.status}"

    class Meta:
        db_table = 'issues'

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE ,null=True, blank=True)
    comment = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} {self.issue.title} {self.author.username}"

    class Meta:
        db_table = 'comments'
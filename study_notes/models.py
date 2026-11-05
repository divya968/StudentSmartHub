from django.db import models
from django.contrib.auth.models import User


class StudyNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    content = models.TextField()
    attachment = models.FileField(
        upload_to='notes_attachments/',
        blank=True,
        null=True
    )
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

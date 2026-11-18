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
    is_pinned = models.BooleanField(default=False)
    tags = models.CharField(max_length=200, blank=True, help_text='Comma separated, e.g. exam, unit-3')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-updated_at']

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def __str__(self):
        return self.title

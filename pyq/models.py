from django.db import models


class PYQuestion(models.Model):
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=150)
    question = models.TextField()
    year = models.PositiveIntegerField()
    exam_name = models.CharField(max_length=150, blank=True)
    marks = models.PositiveIntegerField(default=0)
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subject', 'year']

    def __str__(self):
        return f"{self.subject} - {self.year} - {self.question[:50]}"


class PYQUpload(models.Model):
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to='pyq_uploads/')
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return self.file_name

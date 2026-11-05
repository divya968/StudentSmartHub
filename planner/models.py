from django.db import models
from django.contrib.auth.models import User

class StudyTask(models.Model):
    PRIORITY_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["completed", "due_date"]

    def __str__(self):
        return self.title

class StudyActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    study_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-study_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "study_date"],
                name="unique_user_study_date"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.study_date}"

class StudyGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_date = models.DateField()
    target_hours = models.DecimalField(max_digits=5, decimal_places=2, default=4)
    studied_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    target_tasks = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ["-goal_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "goal_date"],
                name="unique_user_study_goal_date"
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.goal_date}"


from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    SEMESTER_CHOICES = [
        ("1", "Semester 1"),
        ("2", "Semester 2"),
        ("3", "Semester 3"),
        ("4", "Semester 4"),
        ("5", "Semester 5"),
        ("6", "Semester 6"),
        ("7", "Semester 7"),
        ("8", "Semester 8"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    course = models.CharField(max_length=100)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

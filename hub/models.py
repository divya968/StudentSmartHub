from django.conf import settings
from django.db import models
from django.utils import timezone


class FocusSession(models.Model):
    """One completed Pomodoro / focus block."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    minutes = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.minutes}m"


class Exam(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    subject = models.CharField(max_length=100, blank=True)
    exam_date = models.DateField()

    class Meta:
        ordering = ["exam_date"]

    def __str__(self):
        return self.name

    @property
    def days_left(self):
        return (self.exam_date - timezone.localdate()).days


class SyllabusSubject(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_user_syllabus_subject")
        ]

    def __str__(self):
        return self.name

    @property
    def progress(self):
        total = self.chapters.count()
        if not total:
            return 0
        return round(self.chapters.filter(done=True).count() * 100 / total)


class Chapter(models.Model):
    subject = models.ForeignKey(SyllabusSubject, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Flashcard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    question = models.TextField()
    answer = models.TextField()
    known = models.BooleanField(default=False)
    times_reviewed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:50]


class TimetableSlot(models.Model):
    DAYS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
            (4, "Friday"), (5, "Saturday"), (6, "Sunday")]
    KINDS = [("class", "Class"), ("study", "Self Study"), ("break", "Break / Other")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    day = models.PositiveSmallIntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=KINDS, default="class")

    class Meta:
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.get_day_display()} {self.title}"


class StreakFreezeUse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    used_for = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

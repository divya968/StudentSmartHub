from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from hub.models import Exam
from planner.models import StudyTask


class Command(BaseCommand):
    help = ("Email students their tasks due today/tomorrow, overdue tasks and exams within 3 days. "
            "Run once a day (e.g. a Render Cron Job: python manage.py send_reminders).")

    def handle(self, *args, **opts):
        today = timezone.localdate()
        sent = 0
        for user in get_user_model().objects.filter(is_active=True).exclude(email=""):
            tasks = StudyTask.objects.filter(user=user, completed=False, due_date__lte=today + timedelta(days=1))
            exams = Exam.objects.filter(user=user, exam_date__gte=today, exam_date__lte=today + timedelta(days=3))
            if not tasks and not exams:
                continue
            lines = [f"Hi {user.first_name or user.username},", "", "Here is your study reminder:", ""]
            if tasks:
                lines.append("Tasks:")
                for t in tasks:
                    tag = "OVERDUE" if t.due_date < today else ("due today" if t.due_date == today else "due tomorrow")
                    lines.append(f"  - {t.title} ({t.subject}) - {tag}")
                lines.append("")
            if exams:
                lines.append("Upcoming exams:")
                for e in exams:
                    lines.append(f"  - {e.name} in {e.days_left} day(s) ({e.exam_date:%d %b})")
                lines.append("")
            lines.append("Keep going - every study session counts!\n- Student Smart Hub")
            send_mail("📚 Your study reminder", "\n".join(lines), settings.DEFAULT_FROM_EMAIL, [user.email])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Reminders sent to {sent} student(s)."))

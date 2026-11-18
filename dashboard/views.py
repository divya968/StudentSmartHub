import random

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from hub import services
from hub.models import Exam
from planner.models import StudyTask
from planner.views import calculate_streaks
from pyq.models import PYQuestion
from study_notes.models import StudyNote

QUOTES = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Small daily improvements lead to stunning results.", "Robin Sharma"),
    ("Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln"),
    ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar"),
    ("Push yourself, because no one else is going to do it for you.", "Unknown"),
]


@login_required
def dashboard_view(request):
    user = request.user
    profile = getattr(user, "student_profile", None)
    tasks = StudyTask.objects.filter(user=user)

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(completed=True).count()
    pending_tasks = tasks.filter(completed=False).count()
    progress_percentage = round(completed_tasks * 100 / total_tasks) if total_tasks else 0

    today = timezone.localdate()
    stats = services.user_stats(user)
    quote = QUOTES[today.toordinal() % len(QUOTES)]

    context = {
        "profile": profile,
        "total_notes": StudyNote.objects.filter(user=user).count(),
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_pyqs": PYQuestion.objects.count(),
        "progress_percentage": progress_percentage,
        "level": services.level_info(stats["xp"]),
        "streaks": calculate_streaks(user),
        "weekly": services.weekly_stats(user),
        "subjects_chart": services.subject_distribution(user),
        "heat": services.heatmap(user),
        "goal": services.todays_goal(user),
        "exams": Exam.objects.filter(user=user, exam_date__gte=today)[:3],
        "upcoming": services.upcoming_tasks(user),
        "badges_earned": sum(1 for b in services.badges_for(user, stats) if b["earned"]),
        "quote": quote,
        "today": today,
    }
    return render(request, "dashboard/home.html", context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from planner.models import StudyTask
from study_notes.models import StudyNote
from pyq.models import PYQuestion


@login_required
def dashboard_view(request):
    profile = getattr(request.user, "student_profile", None)

    total_notes = StudyNote.objects.filter(
        user=request.user
    ).count()

    total_tasks = StudyTask.objects.filter(
        user=request.user
    ).count()

    completed_tasks = StudyTask.objects.filter(
        user=request.user,
        completed=True
    ).count()

    pending_tasks = StudyTask.objects.filter(
        user=request.user,
        completed=False
    ).count()

    total_pyqs = PYQuestion.objects.count()

    progress_percentage = (
        round((completed_tasks / total_tasks) * 100)
        if total_tasks > 0 else 0
    )

    context = {
        "profile": profile,
        "total_notes": total_notes,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_pyqs": total_pyqs,
        "progress_percentage": progress_percentage,
    }

    return render(request, "dashboard/home.html", context)

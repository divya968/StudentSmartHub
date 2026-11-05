from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import StudyTask, StudyActivity, StudyGoal
from .forms import StudyTaskForm, StudyGoalForm


def calculate_streaks(user):
    today = timezone.localdate()

    dates = list(
        StudyActivity.objects.filter(user=user)
        .order_by("study_date")
        .values_list("study_date", flat=True)
    )

    today_done = today in dates

    current_streak = 0
    streak_start = today if today_done else today - timedelta(days=1)

    if streak_start in dates:
        current_streak = 1
        check_date = streak_start - timedelta(days=1)

        while check_date in dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    longest_streak = 0
    running_streak = 0
    previous_date = None

    for activity_date in dates:
        if previous_date and activity_date == previous_date + timedelta(days=1):
            running_streak += 1
        else:
            running_streak = 1

        longest_streak = max(longest_streak, running_streak)
        previous_date = activity_date

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "today_done": today_done,
    }


@login_required
def task_list(request):
    tasks = StudyTask.objects.filter(user=request.user)
    today = timezone.localdate()

    context = {
        "tasks": tasks,
        "today": today,
        "total": tasks.count(),
        "completed_count": tasks.filter(completed=True).count(),
        "pending_count": tasks.filter(completed=False).count(),
        "overdue_count": tasks.filter(
            completed=False,
            due_date__lt=today
        ).count(),
        **calculate_streaks(request.user),
    }

    return render(request, "planner/task_list.html", context)


@login_required
def task_create(request):
    form = StudyTaskForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()

        messages.success(request, "Study task added successfully!")
        return redirect("planner:list")

    return render(request, "planner/task_form.html", {
        "form": form,
        "heading": "Add Study Task"
    })


@login_required
def task_edit(request, pk):
    task = get_object_or_404(
        StudyTask,
        pk=pk,
        user=request.user
    )

    form = StudyTaskForm(request.POST or None, instance=task)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Task updated successfully!")
        return redirect("planner:list")

    return render(request, "planner/task_form.html", {
        "form": form,
        "heading": "Edit Study Task"
    })


@login_required
def task_delete(request, pk):
    task = get_object_or_404(
        StudyTask,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted.")

    return redirect("planner:list")


@login_required
def task_toggle(request, pk):
    task = get_object_or_404(
        StudyTask,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        task.completed = not task.completed

        if task.completed:
            task.completed_at = timezone.now()
        else:
            task.completed_at = None

        task.save()

    return redirect("planner:list")


@login_required
def study_checkin(request):
    if request.method == "POST":
        today = timezone.localdate()

        activity, created = StudyActivity.objects.get_or_create(
            user=request.user,
            study_date=today
        )

        if created:
            messages.success(
                request,
                "Great! Today's study activity recorded."
            )
        else:
            messages.info(
                request,
                "Today's study activity is already recorded."
            )

    return redirect("planner:list")


@login_required
def study_goal_view(request):
    today = timezone.localdate()

    goal, created = StudyGoal.objects.get_or_create(
        user=request.user,
        goal_date=today
    )

    if request.method == "POST":
        form = StudyGoalForm(request.POST, instance=goal)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Daily study goal updated successfully!"
            )
            return redirect("planner:goals")
    else:
        form = StudyGoalForm(instance=goal)

    completed_today = StudyTask.objects.filter(
        user=request.user,
        completed=True,
        completed_at__date=today
    ).count()

    hours_percentage = min(
        round(float(goal.studied_hours) / float(goal.target_hours) * 100)
        if goal.target_hours else 0,
        100
    )

    tasks_percentage = min(
        round(completed_today / goal.target_tasks * 100)
        if goal.target_tasks else 0,
        100
    )

    context = {
        "form": form,
        "goal": goal,
        "completed_today": completed_today,
        "hours_percentage": hours_percentage,
        "tasks_percentage": tasks_percentage,
    }

    return render(request, "planner/study_goals.html", context)

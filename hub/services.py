"""Business logic for gamification, charts and statistics (kept out of views)."""
import math
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone

from planner.models import StudyActivity, StudyGoal, StudyTask
from study_notes.models import StudyNote

from .models import Chapter, Flashcard, FocusSession, StreakFreezeUse, SyllabusSubject

User = get_user_model()

# ------------------------------------------------------------------ XP / levels
XP_PER_TASK = 10
XP_PER_NOTE = 5
XP_PER_FLASHCARD = 2
XP_PER_CHAPTER = 8
XP_PER_FOCUS_MINUTE = 1

LEVEL_TITLES = {1: "Beginner", 2: "Learner", 3: "Scholar", 4: "Achiever",
                5: "Expert", 6: "Master", 7: "Legend"}


def _collect(user_ids=None):
    """Return {user_id: {component: value}} using a handful of grouped queries."""
    def flt(qs, field="user_id"):
        return qs.filter(**{f"{field}__in": user_ids}) if user_ids is not None else qs

    data = defaultdict(lambda: {"tasks": 0, "notes": 0, "cards": 0, "chapters": 0, "minutes": 0})

    for row in flt(StudyTask.objects.filter(completed=True)).values("user_id").annotate(c=Count("id")):
        data[row["user_id"]]["tasks"] = row["c"]
    for row in flt(StudyNote.objects.all()).values("user_id").annotate(c=Count("id")):
        data[row["user_id"]]["notes"] = row["c"]
    for row in flt(Flashcard.objects.all()).values("user_id").annotate(c=Count("id")):
        data[row["user_id"]]["cards"] = row["c"]
    for row in flt(FocusSession.objects.all()).values("user_id").annotate(m=Sum("minutes")):
        data[row["user_id"]]["minutes"] = row["m"] or 0
    chap = Chapter.objects.filter(done=True)
    if user_ids is not None:
        chap = chap.filter(subject__user_id__in=user_ids)
    for row in chap.values("subject__user_id").annotate(c=Count("id")):
        data[row["subject__user_id"]]["chapters"] = row["c"]
    return data


def _xp_from(parts):
    return (parts["tasks"] * XP_PER_TASK + parts["notes"] * XP_PER_NOTE
            + parts["cards"] * XP_PER_FLASHCARD + parts["chapters"] * XP_PER_CHAPTER
            + parts["minutes"] * XP_PER_FOCUS_MINUTE)


def user_stats(user):
    parts = dict(_collect([user.id])[user.id])
    for key in ("tasks", "notes", "cards", "chapters", "minutes"):
        parts.setdefault(key, 0)
    parts["xp"] = _xp_from(parts)
    return parts


def level_for_xp(xp):
    return int(math.sqrt(max(xp, 0) / 50)) + 1


def level_info(xp):
    level = level_for_xp(xp)
    floor_xp = 50 * (level - 1) ** 2
    next_xp = 50 * level ** 2
    span = next_xp - floor_xp
    pct = round((xp - floor_xp) * 100 / span) if span else 100
    return {
        "xp": xp, "level": level,
        "title": LEVEL_TITLES.get(level, LEVEL_TITLES[7]),
        "floor": floor_xp, "next": next_xp,
        "pct": max(0, min(100, pct)), "to_next": max(next_xp - xp, 0),
    }


def get_level_info(user):
    return level_info(user_stats(user)["xp"])


# ------------------------------------------------------------------ streaks & freezes
def freeze_info(user, level=None):
    if level is None:
        level = get_level_info(user)["level"]
    granted = 1 + level // 3
    used = StreakFreezeUse.objects.filter(user=user).count()
    return {"granted": granted, "used": used, "available": max(granted - used, 0)}


def use_streak_freeze(user):
    """Protect yesterday's streak day. Returns (ok, message)."""
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    info = freeze_info(user)
    if info["available"] <= 0:
        return False, "No streak freezes left. Level up to earn more!"
    if StudyActivity.objects.filter(user=user, study_date=yesterday).exists():
        return False, "Yesterday is already covered - no freeze needed."
    if not StudyActivity.objects.filter(user=user, study_date=yesterday - timedelta(days=1)).exists():
        return False, "A freeze only works if your streak was alive the day before yesterday."
    StudyActivity.objects.create(user=user, study_date=yesterday)
    StreakFreezeUse.objects.create(user=user, used_for=yesterday)
    return True, "Streak freeze used - your streak is safe! 🧊"


# ------------------------------------------------------------------ badges
def badges_for(user, stats=None):
    from planner.views import calculate_streaks
    stats = stats or user_stats(user)
    longest = calculate_streaks(user)["longest_streak"]
    full_subject = any(
        s.chapters.count() >= 3 and s.progress == 100
        for s in SyllabusSubject.objects.filter(user=user).prefetch_related("chapters")
    )
    defs = [
        ("🚀", "First Step", "Complete your first task", stats["tasks"] >= 1),
        ("✅", "Task Crusher", "Complete 50 tasks", stats["tasks"] >= 50),
        ("📝", "Note Taker", "Write 10 notes", stats["notes"] >= 10),
        ("🔥", "Week Warrior", "Reach a 7-day streak", longest >= 7),
        ("⚡", "Unstoppable", "Reach a 30-day streak", longest >= 30),
        ("⏱️", "Focus Hero", "Focus for 5 hours in total", stats["minutes"] >= 300),
        ("🏃", "Marathoner", "Focus for 25 hours in total", stats["minutes"] >= 1500),
        ("🃏", "Card Shark", "Create 25 flashcards", stats["cards"] >= 25),
        ("📖", "Syllabus Slayer", "Finish a subject (3+ chapters)", full_subject),
        ("👑", "Level 5", "Reach level 5", level_for_xp(stats["xp"]) >= 5),
    ]
    return [{"icon": i, "name": n, "desc": d, "earned": bool(e)} for i, n, d, e in defs]


# ------------------------------------------------------------------ leaderboard
def leaderboard(limit=10):
    data = _collect(None)
    rows = []
    users = User.objects.filter(id__in=list(data.keys()), is_active=True)
    for u in users:
        parts = data[u.id]
        xp = _xp_from(parts)
        if xp <= 0:
            continue
        rows.append({
            "user": u,
            "name": u.first_name or u.username,
            "xp": xp,
            "level": level_for_xp(xp),
        })
    rows.sort(key=lambda r: (-r["xp"], r["name"].lower()))
    for i, r in enumerate(rows[:limit], start=1):
        r["rank"] = i
    return rows[:limit]


# ------------------------------------------------------------------ charts
def weekly_stats(user, days=7):
    today = timezone.localdate()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    goals = {g.goal_date: float(g.studied_hours)
             for g in StudyGoal.objects.filter(user=user, goal_date__in=dates)}
    done = defaultdict(int)
    for t in StudyTask.objects.filter(user=user, completed=True,
                                      completed_at__date__gte=dates[0]):
        done[timezone.localtime(t.completed_at).date()] += 1
    return {
        "labels": [d.strftime("%a %d") for d in dates],
        "hours": [round(goals.get(d, 0), 2) for d in dates],
        "tasks": [done.get(d, 0) for d in dates],
        "total_hours": round(sum(goals.get(d, 0) for d in dates), 1),
    }


def subject_distribution(user):
    counts = defaultdict(int)
    for row in StudyTask.objects.filter(user=user).values("subject").annotate(c=Count("id")):
        counts[(row["subject"] or "General").strip().title()] += row["c"]
    for row in StudyNote.objects.filter(user=user).values("subject").annotate(c=Count("id")):
        counts[(row["subject"] or "General").strip().title()] += row["c"]
    for row in Flashcard.objects.filter(user=user).values("subject").annotate(c=Count("id")):
        counts[(row["subject"] or "General").strip().title()] += row["c"]
    items = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    return {"labels": [k for k, _ in items], "values": [v for _, v in items]}


def heatmap(user, weeks=26):
    """GitHub-style grid. Returns list of weeks, each a list of 7 day dicts."""
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)

    score = defaultdict(int)
    for d in StudyActivity.objects.filter(user=user, study_date__gte=start).values_list("study_date", flat=True):
        score[d] += 20
    for g in StudyGoal.objects.filter(user=user, goal_date__gte=start):
        score[g.goal_date] += int(float(g.studied_hours) * 30)
    for s in FocusSession.objects.filter(user=user, created_at__date__gte=start):
        score[timezone.localtime(s.created_at).date()] += s.minutes
    for t in StudyTask.objects.filter(user=user, completed=True, completed_at__date__gte=start):
        score[timezone.localtime(t.completed_at).date()] += 15

    def level(v):
        return 0 if v <= 0 else 1 if v < 30 else 2 if v < 60 else 3 if v < 120 else 4

    grid, active_days = [], 0
    for w in range(weeks):
        col = []
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            future = day > today
            lv = 0 if future else level(score.get(day, 0))
            if lv:
                active_days += 1
            col.append({"date": day, "level": lv, "future": future,
                        "tip": f"{day.strftime('%d %b %Y')}: {score.get(day, 0)} pts" if not future else ""})
        grid.append(col)
    return {"weeks": grid, "active_days": active_days}


def upcoming_tasks(user, limit=5):
    return (StudyTask.objects.filter(user=user, completed=False)
            .order_by("due_date")[:limit])


def todays_goal(user):
    today = timezone.localdate()
    goal = StudyGoal.objects.filter(user=user, goal_date=today).first()
    if not goal:
        return {"hours": 0, "target": 4, "pct": 0}
    target = float(goal.target_hours) or 1
    hrs = float(goal.studied_hours)
    return {"hours": round(hrs, 2), "target": target, "pct": min(round(hrs * 100 / target), 100)}


def add_study_minutes(user, minutes):
    """Add focus minutes to today's goal and record today's activity.

    Recalculate focus hours from today's saved sessions.
    Preserve any manually entered study hours.
    """
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    start = timezone.make_aware(
        datetime.combine(today, time.min)
    )
    end = timezone.make_aware(
        datetime.combine(tomorrow, time.min)
    )

    goal, _ = StudyGoal.objects.get_or_create(
        user=user,
        goal_date=today,
    )

    total = (
        FocusSession.objects.filter(
            user=user,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("minutes"))["total"] or 0
    )

    previous_total = max(total - minutes, 0)

    cent = Decimal("0.01")

    previous_focus_hours = (
        Decimal(previous_total) / Decimal("60")
    ).quantize(cent)

    current_focus_hours = (
        Decimal(total) / Decimal("60")
    ).quantize(cent)

    manual_hours = max(
        Decimal(str(goal.studied_hours)) - previous_focus_hours,
        Decimal("0"),
    )

    goal.studied_hours = min(
        manual_hours + current_focus_hours,
        Decimal("999.99"),
    )

    goal.save(update_fields=["studied_hours"])

    StudyActivity.objects.get_or_create(
        user=user,
        study_date=today,
    )

    return goal


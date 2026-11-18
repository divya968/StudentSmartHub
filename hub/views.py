
import calendar as pycal
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from planner.models import StudyTask
from pyq.models import PYQuestion
from study_notes.models import StudyNote

from . import ai, exports, services
from .forms import ExamForm, FlashcardForm, TimetableSlotForm
from .models import (
    Chapter,
    Exam,
    Flashcard,
    FocusSession,
    SyllabusSubject,
    TimetableSlot,
)

AI_DAILY_LIMIT = 60


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _json_body(request):
    try:
        data = json.loads(request.body or "{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _ai_quota(user):
    key = f"ai-quota:{user.id}:{timezone.localdate()}"
    used = cache.get(key, 0)

    if used >= AI_DAILY_LIMIT:
        return False

    cache.set(key, used + 1, 60 * 60 * 26)
    return True


# ------------------------------------------------------------------
# Achievements
# ------------------------------------------------------------------

@login_required
def achievements(request):
    stats = services.user_stats(request.user)
    info = services.level_info(stats["xp"])

    from planner.views import calculate_streaks

    return render(request, "hub/achievements.html", {
        "stats": stats,
        "info": info,
        "badges": services.badges_for(request.user, stats),
        "board": services.leaderboard(10),
        "freeze": services.freeze_info(request.user, info["level"]),
        "streaks": calculate_streaks(request.user),
        "xp_rules": [
            ("Complete a task", services.XP_PER_TASK),
            ("Write a note", services.XP_PER_NOTE),
            ("Finish a syllabus chapter", services.XP_PER_CHAPTER),
            ("Create a flashcard", services.XP_PER_FLASHCARD),
            ("Each focus minute", services.XP_PER_FOCUS_MINUTE),
        ],
    })


@login_required
@require_POST
def freeze_use(request):
    ok, msg = services.use_streak_freeze(request.user)
    (messages.success if ok else messages.info)(request, msg)
    return redirect("hub:achievements")


# ------------------------------------------------------------------
# Focus timer
# ------------------------------------------------------------------

@login_required
def focus(request):
    today = timezone.localdate()

    sessions = FocusSession.objects.filter(
        user=request.user,
        created_at__date=today,
    )

    minutes = sum(s.minutes for s in sessions)

    subjects = sorted({
        s for s in StudyTask.objects.filter(
            user=request.user
        ).values_list("subject", flat=True) if s
    })

    return render(request, "hub/focus.html", {
        "sessions": sessions[:8],
        "minutes_today": minutes,
        "count_today": sessions.count(),
        "subjects": subjects,
        "goal": services.todays_goal(request.user),
    })


@login_required
@require_POST
def focus_log(request):
    data = _json_body(request)

    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid minutes"}, status=400)

    if not 1 <= minutes <= 180:
        return JsonResponse({
            "error": "minutes must be between 1 and 180"
        }, status=400)

    subject = str(data.get("subject", ""))[:100].strip()

    before = services.get_level_info(request.user)["level"]

    FocusSession.objects.create(
        user=request.user,
        subject=subject,
        minutes=minutes,
    )

    goal = services.add_study_minutes(request.user, minutes)
    info = services.get_level_info(request.user)

    return JsonResponse({
        "ok": True,
        "xp_gained": minutes * services.XP_PER_FOCUS_MINUTE,
        "xp": info["xp"],
        "level": info["level"],
        "level_up": info["level"] > before,
        "studied_hours": float(goal.studied_hours),
    })


# ------------------------------------------------------------------
# Exams
# ------------------------------------------------------------------

@login_required
def exams(request):
    form = ExamForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        exam = form.save(commit=False)
        exam.user = request.user
        exam.save()

        messages.success(request, "Exam added - countdown started! ⏳")
        return redirect("hub:exams")

    today = timezone.localdate()

    qs = Exam.objects.filter(user=request.user)

    return render(request, "hub/exams.html", {
        "form": form,
        "upcoming": qs.filter(exam_date__gte=today),
        "past": qs.filter(exam_date__lt=today).order_by("-exam_date")[:5],
    })


@login_required
@require_POST
def exam_delete(request, pk):
    get_object_or_404(
        Exam,
        pk=pk,
        user=request.user,
    ).delete()

    messages.success(request, "Exam removed.")
    return redirect("hub:exams")


# ------------------------------------------------------------------
# Calendar
# ------------------------------------------------------------------

@login_required
def calendar_view(request):
    today = timezone.localdate()

    try:
        year = int(request.GET.get("y", today.year))
        month = int(request.GET.get("m", today.month))
        date(year, month, 1)
    except (TypeError, ValueError):
        year, month = today.year, today.month

    weeks = pycal.Calendar(
        firstweekday=0
    ).monthdatescalendar(year, month)

    first, last = weeks[0][0], weeks[-1][-1]
    items = {}

    for task in StudyTask.objects.filter(
        user=request.user,
        due_date__range=(first, last),
    ):
        cls = "done" if task.completed else task.priority.lower()

        items.setdefault(task.due_date, []).append({
            "label": task.title,
            "cls": cls,
            "kind": "task",
        })

    for exam in Exam.objects.filter(
        user=request.user,
        exam_date__range=(first, last),
    ):
        items.setdefault(exam.exam_date, []).append({
            "label": "🎓 " + exam.name,
            "cls": "exam",
            "kind": "exam",
        })

    grid = []

    for week in weeks:
        grid.append([
            {
                "date": day,
                "in_month": day.month == month,
                "today": day == today,
                "items": items.get(day, [])[:3],
                "more": max(len(items.get(day, [])) - 3, 0),
            }
            for day in week
        ])

    prev_y, prev_m = (
        (year - 1, 12) if month == 1 else (year, month - 1)
    )

    next_y, next_m = (
        (year + 1, 1) if month == 12 else (year, month + 1)
    )

    return render(request, "hub/calendar.html", {
        "grid": grid,
        "title": date(year, month, 1).strftime("%B %Y"),
        "prev": f"?y={prev_y}&m={prev_m}",
        "next": f"?y={next_y}&m={next_m}",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    })


# ------------------------------------------------------------------
# Syllabus
# ------------------------------------------------------------------

@login_required
def syllabus(request):
    subjects = SyllabusSubject.objects.filter(
        user=request.user
    ).prefetch_related("chapters")

    total = sum(s.chapters.count() for s in subjects)
    done = sum(s.chapters.filter(done=True).count() for s in subjects)

    return render(request, "hub/syllabus.html", {
        "subjects": subjects,
        "overall": round(done * 100 / total) if total else 0,
        "total": total,
        "done": done,
    })


@login_required
@require_POST
def syllabus_add_subject(request):
    name = request.POST.get("name", "").strip()[:100]

    if not name:
        messages.error(request, "Please enter a subject name.")
    else:
        subject, created = SyllabusSubject.objects.get_or_create(
            user=request.user,
            name=name,
        )

        chapters = [
            c.strip()
            for c in request.POST.get("chapters", "").splitlines()
            if c.strip()
        ][:60]

        base = subject.chapters.count()

        Chapter.objects.bulk_create([
            Chapter(
                subject=subject,
                title=c[:200],
                order=base + i,
            )
            for i, c in enumerate(chapters)
        ])

        messages.success(
            request,
            f"Subject '{name}' added with {len(chapters)} chapter(s).",
        )

    return redirect("hub:syllabus")


@login_required
@require_POST
def chapter_add(request, pk):
    subject = get_object_or_404(
        SyllabusSubject,
        pk=pk,
        user=request.user,
    )

    chapters = [
        c.strip()
        for c in request.POST.get("chapters", "").splitlines()
        if c.strip()
    ][:60]

    base = subject.chapters.count()

    Chapter.objects.bulk_create([
        Chapter(
            subject=subject,
            title=c[:200],
            order=base + i,
        )
        for i, c in enumerate(chapters)
    ])

    return redirect("hub:syllabus")


@login_required
@require_POST
def chapter_toggle(request, pk):
    chapter = get_object_or_404(
        Chapter,
        pk=pk,
        subject__user=request.user,
    )

    chapter.done = not chapter.done
    chapter.save(update_fields=["done"])

    subject = chapter.subject

    payload = {
        "done": chapter.done,
        "progress": subject.progress,
        "xp": services.get_level_info(request.user)["xp"],
    }

    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse(payload)

    return redirect("hub:syllabus")


@login_required
@require_POST
def chapter_delete(request, pk):
    get_object_or_404(
        Chapter,
        pk=pk,
        subject__user=request.user,
    ).delete()

    return redirect("hub:syllabus")


@login_required
@require_POST
def syllabus_delete_subject(request, pk):
    get_object_or_404(
        SyllabusSubject,
        pk=pk,
        user=request.user,
    ).delete()

    messages.success(request, "Subject removed.")
    return redirect("hub:syllabus")


# ------------------------------------------------------------------
# Flashcards
# ------------------------------------------------------------------

@login_required
def flashcards(request):
    form = FlashcardForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        card = form.save(commit=False)
        card.user = request.user
        card.save()

        messages.success(request, "Flashcard added! 🃏")
        return redirect("hub:flashcards")

    subject = request.GET.get("subject", "").strip()

    cards = Flashcard.objects.filter(user=request.user)

    all_subjects = sorted({
        s for s in cards.values_list("subject", flat=True) if s
    })

    if subject:
        cards = cards.filter(subject__iexact=subject)

    return render(request, "hub/flashcards.html", {
        "form": form,
        "cards": cards,
        "subjects": all_subjects,
        "selected": subject,
        "notes": StudyNote.objects.filter(user=request.user),
        "known": cards.filter(known=True).count(),
    })


@login_required
def flashcard_study(request):
    subject = request.GET.get("subject", "").strip()

    cards = Flashcard.objects.filter(user=request.user)

    if subject:
        cards = cards.filter(subject__iexact=subject)

    if request.GET.get("unknown"):
        cards = cards.filter(known=False)

    deck = [
        {
            "id": c.id,
            "q": c.question,
            "a": c.answer,
            "subject": c.subject,
        }
        for c in cards.order_by("?")[:50]
    ]

    return render(request, "hub/flashcard_study.html", {
        "deck": deck,
        "subject": subject,
    })


@login_required
@require_POST
def flashcard_mark(request, pk):
    card = get_object_or_404(
        Flashcard,
        pk=pk,
        user=request.user,
    )

    card.known = bool(_json_body(request).get("known"))
    card.times_reviewed += 1
    card.save(update_fields=["known", "times_reviewed"])

    return JsonResponse({"ok": True})


@login_required
@require_POST
def flashcard_delete(request, pk):
    get_object_or_404(
        Flashcard,
        pk=pk,
        user=request.user,
    ).delete()

    return redirect("hub:flashcards")


@login_required
@require_POST
def flashcards_from_note(request, pk):
    note = get_object_or_404(
        StudyNote,
        pk=pk,
        user=request.user,
    )

    if not _ai_quota(request.user):
        messages.error(
            request,
            "Daily AI limit reached. Try again tomorrow.",
        )
        return redirect("hub:flashcards")

    result = ai.make_flashcards(note.content)

    existing = set(
        Flashcard.objects.filter(
            user=request.user
        ).values_list("question", flat=True)
    )

    new = [
        Flashcard(
            user=request.user,
            subject=note.subject,
            question=q[:1000],
            answer=a[:2000],
        )
        for q, a in result["cards"]
        if q not in existing
    ]

    Flashcard.objects.bulk_create(new)

    messages.success(
        request,
        f"Created {len(new)} flashcard(s) from '{note.title}' 🃏 "
        f"({result['mode']} mode)",
    )

    return redirect("hub:flashcards")


# ------------------------------------------------------------------
# Timetable
# ------------------------------------------------------------------

@login_required
def timetable(request):
    form = TimetableSlotForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        slot = form.save(commit=False)
        slot.user = request.user
        slot.save()

        messages.success(request, "Slot added to your timetable 🕒")
        return redirect("hub:timetable")

    slots = TimetableSlot.objects.filter(user=request.user)

    columns = []

    for num, label in TimetableSlot.DAYS:
        columns.append({
            "num": num,
            "label": label,
            "today": num == timezone.localdate().weekday(),
            "slots": [s for s in slots if s.day == num],
        })

    return render(request, "hub/timetable.html", {
        "form": form,
        "columns": columns,
    })


@login_required
@require_POST
def slot_delete(request, pk):
    get_object_or_404(
        TimetableSlot,
        pk=pk,
        user=request.user,
    ).delete()

    return redirect("hub:timetable")


# ------------------------------------------------------------------
# AI Assistant
# ------------------------------------------------------------------

@login_required
def ai_page(request):
    user_questions = PYQuestion.objects.filter(user=request.user)

    subjects = sorted({
        s for s in user_questions.values_list("subject", flat=True) if s
    })

    return render(request, "hub/ai.html", {
        "notes": StudyNote.objects.filter(user=request.user),
        "ai_on": ai.ai_available(),
        "subjects": subjects,
    })


def _text_from_request(request, data):
    note_id = data.get("note_id")

    if note_id:
        note = StudyNote.objects.filter(
            pk=note_id,
            user=request.user,
        ).first()

        if note:
            return f"{note.title}\n{note.content}"

    return str(data.get("text", ""))[:ai.MAX_INPUT_CHARS]


@login_required
@require_POST
def ai_summary(request):
    data = _json_body(request)
    text = _text_from_request(request, data)

    if len(text.split()) < 8:
        return JsonResponse({
            "error": "Please pick a note or paste at least a few sentences."
        }, status=400)

    if not _ai_quota(request.user):
        return JsonResponse({
            "error": "Daily AI limit reached."
        }, status=429)

    return JsonResponse(ai.summarize(text))


@login_required
@require_POST
def ai_quiz(request):
    data = _json_body(request)
    text = _text_from_request(request, data)

    if len(text.split()) < 20:
        return JsonResponse({
            "error": "Need a longer note (20+ words) to build a quiz."
        }, status=400)

    if not _ai_quota(request.user):
        return JsonResponse({
            "error": "Daily AI limit reached."
        }, status=429)

    result = ai.make_quiz(text, data.get("n", 5))

    if not result["questions"]:
        return JsonResponse({
            "error": "Couldn't build questions from this text. Try a longer note."
        }, status=400)

    return JsonResponse(result)


@login_required
@require_POST
def ai_chat(request):
    data = _json_body(request)

    if not _ai_quota(request.user):
        return JsonResponse({
            "error": "Daily AI limit reached."
        }, status=429)

    notes = list(
        StudyNote.objects.filter(user=request.user)[:200]
    )

    return JsonResponse(ai.chat(data.get("question", ""), notes))


@login_required
@require_GET
def ai_predict(request):
    # Only use questions belonging to the currently logged-in user.
    qs = PYQuestion.objects.filter(user=request.user)

    subject = request.GET.get("subject", "").strip()

    if subject:
        qs = qs.filter(subject__iexact=subject)

    return JsonResponse({
        "rows": ai.predict_pyq(qs)
    })


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------

@login_required
def search(request):
    q = request.GET.get("q", "").strip()[:100]
    results = {}

    if q:
        user = request.user

        results = {
            "notes": StudyNote.objects.filter(
                user=user
            ).filter(
                Q(title__icontains=q) |
                Q(subject__icontains=q) |
                Q(content__icontains=q) |
                Q(tags__icontains=q)
            )[:10],

            "tasks": StudyTask.objects.filter(
                user=user
            ).filter(
                Q(title__icontains=q) |
                Q(subject__icontains=q) |
                Q(description__icontains=q)
            )[:10],

            # PYQs are strictly account-wise.
            "pyqs": PYQuestion.objects.filter(
                user=user
            ).filter(
                Q(question__icontains=q) |
                Q(topic__icontains=q) |
                Q(subject__icontains=q)
            )[:10],

            "cards": Flashcard.objects.filter(
                user=user
            ).filter(
                Q(question__icontains=q) |
                Q(answer__icontains=q)
            )[:10],

            "exams": Exam.objects.filter(
                user=user
            ).filter(
                Q(name__icontains=q) |
                Q(subject__icontains=q)
            )[:10],

            "chapters": Chapter.objects.filter(
                subject__user=user,
                title__icontains=q,
            ).select_related("subject")[:10],
        }

    total = sum(len(list(v)) for v in results.values())

    return render(request, "hub/search.html", {
        "q": q,
        "results": results,
        "total": total,
    })


# ------------------------------------------------------------------
# Exports
# ------------------------------------------------------------------

@login_required
def export_data(request, kind, fmt):
    if fmt not in ("xlsx", "pdf") or kind not in (
        "tasks", "pyq", "exams"
    ):
        raise Http404

    if kind == "tasks":
        title = "My Study Tasks"
        headers = [
            "Title",
            "Subject",
            "Priority",
            "Due date",
            "Status",
        ]

        rows = [
            [
                t.title,
                t.subject,
                t.priority,
                t.due_date.strftime("%d %b %Y"),
                "Completed" if t.completed else "Pending",
            ]
            for t in StudyTask.objects.filter(user=request.user)
        ]

    elif kind == "pyq":
        title = "Previous Year Questions"

        headers = [
            "Subject",
            "Topic",
            "Question",
            "Year",
            "Exam",
            "Marks",
            "Important",
        ]

        # Export only the current user's PYQs.
        rows = [
            [
                q.subject,
                q.topic,
                q.question,
                q.year,
                q.exam_name,
                q.marks,
                "Yes" if q.is_important else "",
            ]
            for q in PYQuestion.objects.filter(user=request.user)
        ]

    else:
        title = "My Exams"

        headers = [
            "Exam",
            "Subject",
            "Date",
            "Days left",
        ]

        rows = [
            [
                e.name,
                e.subject,
                e.exam_date.strftime("%d %b %Y"),
                e.days_left,
            ]
            for e in Exam.objects.filter(user=request.user)
        ]

    if fmt == "xlsx":
        resp = HttpResponse(
            exports.build_xlsx(title, headers, rows),
            content_type=exports.XLSX_MIME,
        )
    else:
        resp = HttpResponse(
            exports.build_table_pdf(title, headers, rows),
            content_type="application/pdf",
        )

    resp["Content-Disposition"] = (
        f'attachment; filename="{kind}.{fmt}"'
    )

    return resp


# ------------------------------------------------------------------
# PWA
# ------------------------------------------------------------------

def manifest(request):
    from django.templatetags.static import static

    data = {
        "name": "Student Smart Hub",
        "short_name": "SmartHub",
        "start_url": "/dashboard/",
        "display": "standalone",
        "background_color": "#f5f3ff",
        "theme_color": "#7c3aed",
        "description": "Your all-in-one study workspace.",
        "icons": [
            {
                "src": static("img/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": static("img/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
            },
            {
                "src": static("img/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }

    return HttpResponse(
        json.dumps(data),
        content_type="application/manifest+json",
    )


def service_worker(request):
    js = """
const CACHE = 'ssh-v2';
const SHELL = ['/offline/'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks =>
      Promise.all(
        ks.filter(k => k !== CACHE).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const req = e.request;

  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(req).then(hit =>
        hit || fetch(req).then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
          return res;
        })
      )
    );
  } else if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).catch(() => caches.match('/offline/'))
    );
  }
});
"""

    resp = HttpResponse(
        js,
        content_type="application/javascript",
    )

    resp["Service-Worker-Allowed"] = "/"

    return resp


def offline(request):
    return render(request, "hub/offline.html")

import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import StudentProfile
from planner.models import StudyActivity, StudyGoal, StudyTask
from pyq.models import PYQuestion
from study_notes.models import StudyNote

from . import ai, services
from .models import Chapter, Exam, Flashcard, FocusSession, SyllabusSubject, TimetableSlot

User = get_user_model()

# The production static storage needs `collectstatic` first; tests use plain storage.
PLAIN_STATIC = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_user(name="alice"):
    u = User.objects.create_user(name, f"{name}@example.com", "pass12345", first_name=name.title())
    StudentProfile.objects.create(user=u, course="CS", semester="3")
    return u


@override_settings(STORAGES=PLAIN_STATIC)
class BaseCase(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob")
        self.client.login(username="alice", password="pass12345")
        self.today = timezone.localdate()

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")


class PagesRender(BaseCase):
    def test_ai_is_available_without_paid_api(self):
        self.assertTrue(ai.ai_available())
        response = self.client.get(reverse("hub:ai"))
        self.assertEqual(response.status_code, 200)
    def test_every_page_loads(self):
        note = StudyNote.objects.create(user=self.user, title="N", subject="S", content="Some **bold** text. " * 10)
        task = StudyTask.objects.create(user=self.user, title="T", subject="S", due_date=self.today)
        names = ["dashboard", "hub:achievements", "hub:focus", "hub:exams", "hub:calendar", "hub:syllabus",
                 "hub:flashcards", "hub:flashcard_study", "hub:timetable", "hub:ai", "hub:search",
                 "planner:board", "planner:list", "planner:goals", "study_notes:list", "pyq:list",
                 "pyq:analytics", "profile", "offline"]
        for n in names:
            r = self.client.get(reverse(n))
            self.assertEqual(r.status_code, 200, n)
        self.assertEqual(self.client.get(reverse("study_notes:detail", args=[note.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("hub:search") + "?q=bold").status_code, 200)

    def test_login_required(self):
        self.client.logout()
        for n in ["hub:focus", "hub:exams", "hub:ai", "planner:board", "dashboard", "hub:achievements"]:
            r = self.client.get(reverse(n))
            self.assertEqual(r.status_code, 302, n)
            self.assertIn("/accounts/login/", r["Location"])
        self.assertEqual(self.client.post(reverse("hub:focus_log")).status_code, 302)

    def test_pwa_files(self):
        self.client.logout()
        m = self.client.get("/manifest.json")
        self.assertEqual(m.status_code, 200)
        self.assertEqual(json.loads(m.content)["short_name"], "SmartHub")
        sw = self.client.get("/sw.js")
        self.assertEqual(sw["Service-Worker-Allowed"], "/")


class Gamification(BaseCase):
    def test_xp_and_levels(self):
        StudyTask.objects.create(user=self.user, title="a", subject="x", due_date=self.today, completed=True)
        StudyNote.objects.create(user=self.user, title="n", subject="x", content="c")
        FocusSession.objects.create(user=self.user, minutes=25)
        self.assertEqual(services.user_stats(self.user)["xp"], 10 + 5 + 25)
        self.assertEqual(services.level_for_xp(0), 1)
        self.assertEqual(services.level_for_xp(50), 2)
        self.assertEqual(services.level_for_xp(200), 3)
        info = services.level_info(75)
        self.assertEqual(info["level"], 2)
        self.assertTrue(0 <= info["pct"] <= 100)

    def test_xp_is_per_user(self):
        FocusSession.objects.create(user=self.other, minutes=100)
        self.assertEqual(services.user_stats(self.user)["xp"], 0)

    def test_badges(self):
        StudyTask.objects.create(user=self.user, title="a", subject="x", due_date=self.today, completed=True)
        earned = {b["name"] for b in services.badges_for(self.user) if b["earned"]}
        self.assertIn("First Step", earned)
        self.assertNotIn("Task Crusher", earned)

    def test_leaderboard_orders_by_xp(self):
        FocusSession.objects.create(user=self.user, minutes=10)
        FocusSession.objects.create(user=self.other, minutes=90)
        board = services.leaderboard()
        self.assertEqual([r["user"] for r in board], [self.other, self.user])
        self.assertEqual(board[0]["rank"], 1)

    def test_streak_freeze(self):
        y = self.today - timedelta(days=1)
        StudyActivity.objects.create(user=self.user, study_date=y - timedelta(days=1))
        r = self.client.post(reverse("hub:freeze"), follow=True)
        self.assertTrue(StudyActivity.objects.filter(user=self.user, study_date=y).exists())
        self.assertEqual(services.freeze_info(self.user)["available"], 0)
        # second use refused
        ok, _ = services.use_streak_freeze(self.user)
        self.assertFalse(ok)

    def test_freeze_refused_without_streak(self):
        ok, msg = services.use_streak_freeze(self.user)
        self.assertFalse(ok)

    def test_heatmap_and_weekly(self):
        StudyActivity.objects.create(user=self.user, study_date=self.today)
        FocusSession.objects.create(user=self.user, minutes=60)
        h = services.heatmap(self.user)
        self.assertEqual(len(h["weeks"]), 26)
        self.assertTrue(all(len(w) == 7 for w in h["weeks"]))
        self.assertGreaterEqual(h["active_days"], 1)
        w = services.weekly_stats(self.user)
        self.assertEqual(len(w["labels"]), 7)


class FocusTimer(BaseCase):
    def test_log_session_updates_goal_streak_xp(self):
        r = self.post_json(reverse("hub:focus_log"), {"minutes": 30, "subject": "DBMS"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["xp_gained"], 30)
        self.assertEqual(FocusSession.objects.filter(user=self.user).count(), 1)
        goal = StudyGoal.objects.get(user=self.user, goal_date=self.today)
        self.assertEqual(float(goal.studied_hours), 0.5)
        self.assertTrue(StudyActivity.objects.filter(user=self.user, study_date=self.today).exists())

    def test_hours_accumulate(self):
        for _ in range(3):
            self.post_json(reverse("hub:focus_log"), {"minutes": 20})
        goal = StudyGoal.objects.get(user=self.user, goal_date=self.today)
        self.assertEqual(float(goal.studied_hours), 1.0)

    def test_validation(self):
        url = reverse("hub:focus_log")
        for bad in ({"minutes": 0}, {"minutes": 999}, {"minutes": "abc"}, {}):
            self.assertEqual(self.post_json(url, bad).status_code, 400, bad)
        self.assertEqual(self.client.post(url, "not json", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get(url).status_code, 405)


class Kanban(BaseCase):
    def test_move_between_columns(self):
        t = StudyTask.objects.create(user=self.user, title="t", subject="s", due_date=self.today)
        url = reverse("planner:move", args=[t.pk])
        r = self.post_json(url, {"column": "doing"})
        t.refresh_from_db()
        self.assertTrue(t.in_progress and not t.completed)
        r = self.post_json(url, {"column": "done"})
        t.refresh_from_db()
        self.assertTrue(t.completed and t.completed_at and not t.in_progress)
        self.assertTrue(r.json()["just_completed"])
        self.post_json(url, {"column": "todo"})
        t.refresh_from_db()
        self.assertFalse(t.completed or t.in_progress or t.completed_at)

    def test_invalid_and_foreign(self):
        t = StudyTask.objects.create(user=self.other, title="t", subject="s", due_date=self.today)
        self.assertEqual(self.post_json(reverse("planner:move", args=[t.pk]), {"column": "done"}).status_code, 404)
        mine = StudyTask.objects.create(user=self.user, title="m", subject="s", due_date=self.today)
        self.assertEqual(self.post_json(reverse("planner:move", args=[mine.pk]), {"column": "nope"}).status_code, 400)


class Syllabus(BaseCase):
    def test_add_toggle_progress(self):
        self.client.post(reverse("hub:syllabus_add"), {"name": "OS", "chapters": "A\nB\n\nC\nD"})
        s = SyllabusSubject.objects.get(user=self.user)
        self.assertEqual(s.chapters.count(), 4)
        c = s.chapters.first()
        r = self.client.post(reverse("hub:chapter_toggle", args=[c.pk]), HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.json()["progress"], 25)
        self.assertEqual(services.user_stats(self.user)["chapters"], 1)

    def test_cannot_touch_others(self):
        s = SyllabusSubject.objects.create(user=self.other, name="X")
        c = Chapter.objects.create(subject=s, title="c")
        self.assertEqual(self.client.post(reverse("hub:chapter_toggle", args=[c.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("hub:syllabus_delete", args=[s.pk])).status_code, 404)

    def test_duplicate_subject_not_duplicated(self):
        for _ in range(2):
            self.client.post(reverse("hub:syllabus_add"), {"name": "OS", "chapters": "A"})
        self.assertEqual(SyllabusSubject.objects.filter(user=self.user).count(), 1)


class ExamsCalendarTimetable(BaseCase):
    def test_exam_countdown(self):
        self.client.post(reverse("hub:exams"), {"name": "Mid", "subject": "DBMS",
                                                 "exam_date": (self.today + timedelta(days=5)).isoformat()})
        e = Exam.objects.get(user=self.user)
        self.assertEqual(e.days_left, 5)

    def test_calendar_shows_items_and_handles_bad_params(self):
        StudyTask.objects.create(user=self.user, title="CalTask", subject="s", due_date=self.today)
        Exam.objects.create(user=self.user, name="CalExam", exam_date=self.today)
        r = self.client.get(reverse("hub:calendar"))
        self.assertContains(r, "CalTask")
        self.assertContains(r, "CalExam")
        self.assertEqual(self.client.get(reverse("hub:calendar") + "?y=abc&m=99").status_code, 200)

    def test_calendar_hides_other_users(self):
        StudyTask.objects.create(user=self.other, title="SecretTask", subject="s", due_date=self.today)
        self.assertNotContains(self.client.get(reverse("hub:calendar")), "SecretTask")

    def test_timetable_validation(self):
        url = reverse("hub:timetable")
        self.client.post(url, {"day": 0, "start_time": "10:00", "end_time": "09:00", "title": "Bad", "kind": "class"})
        self.assertEqual(TimetableSlot.objects.count(), 0)
        self.client.post(url, {"day": 0, "start_time": "09:00", "end_time": "10:00", "title": "Good", "kind": "class"})
        self.assertEqual(TimetableSlot.objects.count(), 1)


class Flashcards(BaseCase):
    def test_from_note_offline(self):
        n = StudyNote.objects.create(user=self.user, title="DB", subject="DBMS",
                                     content="Primary key: uniquely identifies a row in a table\nForeign key: links two tables together")
        self.client.post(reverse("hub:flashcards_from_note", args=[n.pk]))
        qs = Flashcard.objects.filter(user=self.user)
        self.assertEqual(qs.count(), 2)
        self.assertTrue(qs.filter(question="What is Primary key?").exists())
        # running again must not duplicate
        self.client.post(reverse("hub:flashcards_from_note", args=[n.pk]))
        self.assertEqual(Flashcard.objects.filter(user=self.user).count(), 2)

    def test_mark_and_foreign(self):
        c = Flashcard.objects.create(user=self.user, question="q", answer="a")
        self.post_json(reverse("hub:flashcard_mark", args=[c.pk]), {"known": True})
        c.refresh_from_db()
        self.assertTrue(c.known)
        self.assertEqual(c.times_reviewed, 1)
        o = Flashcard.objects.create(user=self.other, question="q", answer="a")
        self.assertEqual(self.post_json(reverse("hub:flashcard_mark", args=[o.pk]), {"known": True}).status_code, 404)

    def test_other_note_forbidden(self):
        n = StudyNote.objects.create(user=self.other, title="x", subject="x", content="word " * 30)
        self.assertEqual(self.client.post(reverse("hub:flashcards_from_note", args=[n.pk])).status_code, 404)


TEXT = ("Photosynthesis is the process plants use to convert sunlight into chemical energy. "
        "Chlorophyll absorbs sunlight inside the chloroplasts of plant cells. "
        "Carbon dioxide and water are converted into glucose and oxygen. "
        "The light reactions happen in the thylakoid membranes while the Calvin cycle occurs in the stroma. "
        "Oxygen released during photosynthesis comes from the splitting of water molecules.")


class AIOffline(BaseCase):
    def test_summary(self):
        out = ai.summarize(TEXT, 2)
        self.assertEqual(out["mode"], "offline")
        self.assertEqual(out["text"].count("- "), 2)

    def test_quiz_structure(self):
        q = ai.make_quiz(TEXT, 3)["questions"]
        self.assertTrue(1 <= len(q) <= 3)
        for item in q:
            self.assertIn("_____", item["q"])
            self.assertEqual(len(set(item["options"])), len(item["options"]))
            self.assertTrue(0 <= item["answer"] < len(item["options"]))

    def test_quiz_endpoint_validation(self):
        self.assertEqual(self.post_json(reverse("hub:ai_quiz"), {"text": "too short"}).status_code, 400)
        r = self.post_json(reverse("hub:ai_quiz"), {"text": TEXT, "n": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["mode"], "offline")

    def test_summary_endpoint_uses_note_and_blocks_foreign_note(self):
        mine = StudyNote.objects.create(user=self.user, title="m", subject="s", content=TEXT)
        self.assertEqual(self.post_json(reverse("hub:ai_summary"), {"note_id": mine.pk}).status_code, 200)
        theirs = StudyNote.objects.create(user=self.other, title="t", subject="s", content=TEXT)
        self.assertEqual(self.post_json(reverse("hub:ai_summary"), {"note_id": theirs.pk}).status_code, 400)

    def test_chat_finds_notes(self):
        n = StudyNote.objects.create(user=self.user, title="Plants", subject="Bio", content=TEXT)
        r = self.post_json(reverse("hub:ai_chat"), {"question": "How does chlorophyll absorb sunlight?"}).json()
        self.assertEqual(r["mode"], "offline")
        self.assertIn("Plants", r["sources"])

    def test_chat_does_not_leak_other_users_notes(self):
        StudyNote.objects.create(user=self.other, title="BobSecret", subject="x", content="quantum entanglement physics experiment")
        r = self.post_json(reverse("hub:ai_chat"), {"question": "quantum entanglement"}).json()
        self.assertEqual(r["sources"], [])
        self.assertNotIn("BobSecret", r["answer"])

    def test_prediction_ranks_frequent_topics(self):
        for y in (2021, 2022, 2023):
            PYQuestion.objects.create(subject="DBMS", topic="Normalization", question="q", year=y, marks=5, is_important=True)
        PYQuestion.objects.create(subject="DBMS", topic="Misc", question="q2", year=2021, marks=2)
        rows = ai.predict_pyq(PYQuestion.objects.all())
        self.assertEqual(rows[0]["topic"], "Normalization")
        self.assertEqual(rows[0]["priority"], 100)
        self.assertLess(rows[1]["priority"], 100)
        self.assertEqual(self.client.get(reverse("hub:ai_predict") + "?subject=dbms").status_code, 200)
        self.assertEqual(ai.predict_pyq(PYQuestion.objects.none()), [])


class AILocalOnly(TestCase):
    def test_assistant_is_local_and_key_free(self):
        note = StudyNote(title="Python files", subject="Python", tags="", content="File handling in Python lets programs create, read, update and delete files. The open function is used to open a file.")
        result = ai.chat("Explain file handling in Python", [note])
        self.assertEqual(result["mode"], "offline")
        self.assertIn("File handling", result["answer"])
        self.assertEqual(ai.make_quiz(TEXT, 2)["mode"], "offline")



class Markdown(TestCase):
    def render(self, text):
        return Template("{% load hub_extras %}{{ t|markdown_lite }}").render(Context({"t": text}))

    def test_basic(self):
        html = self.render("# Title\n- one\n- two\n\n**bold** and *it*")
        self.assertIn("<h3>Title</h3>", html)
        self.assertIn("<li>one</li>", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>it</em>", html)

    def test_xss_is_escaped(self):
        for evil in ("<script>alert(1)</script>", "**<img src=x onerror=alert(1)>**", "- <b onmouseover=x>"):
            html = self.render(evil)
            self.assertNotIn("<script", html)
            self.assertNotIn("<img", html)
            self.assertNotIn("<b ", html)


class NotesFeatures(BaseCase):
    def test_pin_tags_filter_and_ordering(self):
        a = StudyNote.objects.create(user=self.user, title="A", subject="s", content="c", tags="exam, unit-3")
        b = StudyNote.objects.create(user=self.user, title="B", subject="s", content="c")
        self.client.post(reverse("study_notes:pin", args=[a.pk]))
        a.refresh_from_db()
        self.assertTrue(a.is_pinned)
        self.assertEqual(list(StudyNote.objects.filter(user=self.user))[0], a)
        self.assertEqual(a.tag_list, ["exam", "unit-3"])
        r = self.client.get(reverse("study_notes:list") + "?tag=unit-3")
        self.assertContains(r, "A")
        self.assertEqual(len(r.context["notes"]), 1)

    def test_exports(self):
        n = StudyNote.objects.create(user=self.user, title="Exp", subject="s", content="# H\n- x\n<b>tag</b> & stuff")
        pdf = self.client.get(reverse("study_notes:export", args=[n.pk, "pdf"]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        md = self.client.get(reverse("study_notes:export", args=[n.pk, "md"]))
        self.assertContains(md, "# Exp")
        self.assertEqual(self.client.get(reverse("study_notes:export", args=[n.pk, "exe"])).status_code, 404)

    def test_other_user_cannot_view_or_export(self):
        n = StudyNote.objects.create(user=self.other, title="Priv", subject="s", content="x")
        self.assertEqual(self.client.get(reverse("study_notes:detail", args=[n.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("study_notes:export", args=[n.pk, "pdf"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("study_notes:pin", args=[n.pk])).status_code, 404)


class ExportsAndSearch(BaseCase):
    def test_xlsx_and_pdf(self):
        StudyTask.objects.create(user=self.user, title="T1", subject="s", due_date=self.today)
        PYQuestion.objects.create(subject="DBMS", topic="x", question="Q & <A>", year=2023)
        Exam.objects.create(user=self.user, name="E", exam_date=self.today)
        for kind in ("tasks", "pyq", "exams"):
            x = self.client.get(reverse("hub:export", args=[kind, "xlsx"]))
            self.assertEqual(x.status_code, 200)
            self.assertTrue(x.content.startswith(b"PK"))  # zip container
            p = self.client.get(reverse("hub:export", args=[kind, "pdf"]))
            self.assertTrue(p.content.startswith(b"%PDF"))
        self.assertEqual(self.client.get(reverse("hub:export", args=["users", "xlsx"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("hub:export", args=["tasks", "exe"])).status_code, 404)

    def test_export_only_own_tasks(self):
        from openpyxl import load_workbook
        from io import BytesIO
        StudyTask.objects.create(user=self.user, title="MINE", subject="s", due_date=self.today)
        StudyTask.objects.create(user=self.other, title="THEIRS", subject="s", due_date=self.today)
        wb = load_workbook(BytesIO(self.client.get(reverse("hub:export", args=["tasks", "xlsx"])).content))
        values = [c.value for row in wb.active.iter_rows() for c in row]
        self.assertIn("MINE", values)
        self.assertNotIn("THEIRS", values)

    def test_search_scopes_to_user(self):
        StudyNote.objects.create(user=self.user, title="needle note", subject="s", content="c")
        StudyNote.objects.create(user=self.other, title="needle secret", subject="s", content="c")
        r = self.client.get(reverse("hub:search") + "?q=needle")
        self.assertContains(r, "needle note")
        self.assertNotContains(r, "needle secret")


class AuthFeatures(BaseCase):
    def test_password_reset_sends_email(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)
        r = self.client.post(reverse("password_reset"), {"email": "alice@example.com"})
        self.assertRedirects(r, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)

    def test_password_reset_unknown_email_is_silent(self):
        self.client.logout()
        r = self.client.post(reverse("password_reset"), {"email": "nobody@example.com"})
        self.assertRedirects(r, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(DEMO_MODE=False)
    def test_demo_disabled_by_default(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("demo_login")).status_code, 404)
        self.assertNotContains(self.client.get(reverse("login")), "Try the Demo")

    @override_settings(DEMO_MODE=True)
    def test_demo_login_works(self):
        self.client.logout()
        r = self.client.get(reverse("demo_login"))
        self.assertRedirects(r, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertTrue(Exam.objects.filter(user__username="demo").exists())

    def test_google_hidden_without_config(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("google_login")).status_code, 404)
        self.assertNotContains(self.client.get(reverse("login")), "Continue with Google")

    @override_settings(GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="sec")
    def test_google_flow(self):
        self.client.logout()
        r = self.client.get(reverse("google_login"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("accounts.google.com", r["Location"])
        state = self.client.session["google_oauth_state"]
        # wrong state is rejected
        bad = self.client.get(reverse("google_callback") + "?code=x&state=wrong")
        self.assertRedirects(bad, reverse("login"))
        # good flow with mocked Google responses
        self.client.get(reverse("google_login"))
        state = self.client.session["google_oauth_state"]
        responses = [{"access_token": "tok"},
                     {"email": "newbie@gmail.com", "email_verified": True, "given_name": "New", "family_name": "Bie"}]
        with mock.patch("accounts.views._http_json", side_effect=responses):
            r = self.client.get(reverse("google_callback") + f"?code=abc&state={state}")
        self.assertRedirects(r, reverse("dashboard"), fetch_redirect_response=False)
        u = User.objects.get(email="newbie@gmail.com")
        self.assertFalse(u.has_usable_password())
        self.assertTrue(StudentProfile.objects.filter(user=u).exists())

    @override_settings(GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="sec")
    def test_google_unverified_email_rejected(self):
        self.client.logout()
        self.client.get(reverse("google_login"))
        state = self.client.session["google_oauth_state"]
        with mock.patch("accounts.views._http_json",
                        side_effect=[{"access_token": "t"}, {"email": "x@y.com", "email_verified": False}]):
            r = self.client.get(reverse("google_callback") + f"?code=abc&state={state}")
        self.assertRedirects(r, reverse("login"))
        self.assertFalse(User.objects.filter(email="x@y.com").exists())

    def test_avatar_upload(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = BytesIO()
        Image.new("RGB", (20, 20), "red").save(buf, "PNG")
        with override_settings(MEDIA_ROOT="/tmp/ssh_test_media"):
            r = self.client.post(reverse("profile"), {
                "full_name": "Alice A", "email": "alice@example.com", "course": "CS", "semester": "3",
                "avatar": SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")})
            self.assertRedirects(r, reverse("profile"))
        self.user.student_profile.refresh_from_db()
        self.assertTrue(self.user.student_profile.avatar)

    def test_avatar_rejects_non_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        r = self.client.post(reverse("profile"), {
            "full_name": "Alice A", "email": "alice@example.com", "course": "CS", "semester": "3",
            "avatar": SimpleUploadedFile("a.png", b"not an image", content_type="image/png")})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.user.student_profile.avatar)


class Commands(BaseCase):
    def test_send_reminders(self):
        StudyTask.objects.create(user=self.user, title="Due soon", subject="s", due_date=self.today)
        Exam.objects.create(user=self.user, name="BigExam", exam_date=self.today + timedelta(days=2))
        StudyTask.objects.create(user=self.other, title="Far", subject="s", due_date=self.today + timedelta(days=30))
        call_command("send_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])
        self.assertIn("Due soon", mail.outbox[0].body)
        self.assertIn("BigExam", mail.outbox[0].body)

    def test_seed_demo_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")
        self.assertEqual(User.objects.filter(username="demo").count(), 1)
        demo = User.objects.get(username="demo")
        self.assertGreater(StudyTask.objects.filter(user=demo).count(), 3)
        call_command("seed_demo", "--reset")
        self.assertEqual(User.objects.filter(username="demo").count(), 1)

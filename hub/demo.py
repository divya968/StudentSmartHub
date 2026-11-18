
"""Creates a ready-made demo account with realistic data (used for viva / presentations)."""

import random
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import StudentProfile
from planner.models import StudyActivity, StudyGoal, StudyTask
from pyq.models import PYQuestion
from study_notes.models import StudyNote

from .models import (
    Chapter,
    Exam,
    Flashcard,
    FocusSession,
    SyllabusSubject,
    TimetableSlot,
)


DEMO_USERNAME = "demo"


# Only these questions belong to the demo account.
DEMO_PYQ_BANK = [
    (
        "DBMS",
        "Normalization",
        "Explain 3NF with an example.",
        [2021, 2022, 2023],
        5,
        True,
    ),
    (
        "DBMS",
        "Transactions",
        "Explain ACID properties.",
        [2022, 2023],
        5,
        True,
    ),
    (
        "DBMS",
        "SQL",
        "Write a query using GROUP BY and HAVING.",
        [2021, 2023],
        4,
        False,
    ),
    (
        "OS",
        "Scheduling",
        "Compare FCFS and Round Robin.",
        [2021, 2022],
        5,
        True,
    ),
    (
        "OS",
        "Deadlock",
        "Explain Banker's algorithm.",
        [2022],
        8,
        False,
    ),
    (
        "CN",
        "OSI Model",
        "Describe the layers of the OSI model.",
        [2021, 2022, 2023],
        6,
        True,
    ),
]


def ensure_demo_pyqs(user):
    """Create demo sample PYQs only for the demo account."""

    if user.username != DEMO_USERNAME:
        return

    if PYQuestion.objects.filter(user=user).exists():
        return

    for subj, topic, question, years, marks, important in DEMO_PYQ_BANK:
        for year in years:
            PYQuestion.objects.create(
                user=user,
                subject=subj,
                topic=topic,
                question=question,
                year=year,
                exam_name="End Sem",
                marks=marks,
                is_important=important,
            )


def ensure_demo_user(reset=False):
    """Return the existing demo user or create it."""

    User = get_user_model()
    user = User.objects.filter(username=DEMO_USERNAME).first()

    if user and not reset:
        ensure_demo_pyqs(user)
        return user

    if user:
        user.delete()

    return seed_demo()


def seed_demo():
    """Create the demo account and its sample data."""

    User = get_user_model()
    rnd = random.Random(42)
    today = timezone.localdate()

    user = User.objects.create(
        username=DEMO_USERNAME,
        first_name="Demo",
        last_name="Student",
        email="demo@example.com",
    )

    user.set_unusable_password()
    user.save()

    StudentProfile.objects.create(
        user=user,
        course="B.Tech Computer Science",
        semester="4",
    )

    # Sample study tasks
    tasks = [
        ("Finish DBMS unit 3 notes", "DBMS", "High", -1, True),
        ("Revise OS scheduling", "OS", "Medium", 1, False),
        ("Solve CN numericals", "CN", "Low", 2, True),
        ("Practice SQL joins", "DBMS", "High", 3, False),
        ("Read Data Structures ch. 5", "DSA", "Medium", 4, False),
        ("Mock test: Operating Systems", "OS", "High", 6, False),
        ("Prepare viva questions", "DBMS", "Medium", 7, False),
        ("Graph algorithms practice", "DSA", "High", -2, True),
    ]

    now = timezone.now()

    for title, subj, priority, offset, done in tasks:
        StudyTask.objects.create(
            user=user,
            title=title,
            subject=subj,
            priority=priority,
            completed=done,
            description="Sample task from the demo account.",
            due_date=today + timedelta(days=offset),
            completed_at=(
                now - timedelta(days=rnd.randint(0, 3))
            ) if done else None,
            in_progress=(not done and "Revise" in title),
        )

    # Study history for charts and heatmap
    for i in range(120):
        day = today - timedelta(days=i)

        if rnd.random() < (0.85 if i < 10 else 0.5):
            StudyActivity.objects.get_or_create(
                user=user,
                study_date=day,
            )

            hours = round(rnd.uniform(0.5, 4.5), 2)

            if i < 14:
                StudyGoal.objects.update_or_create(
                    user=user,
                    goal_date=day,
                    defaults={
                        "studied_hours": hours,
                        "target_hours": 4,
                        "target_tasks": 5,
                    },
                )

            for _ in range(rnd.randint(0, 2) if i < 30 else 0):
                FocusSession.objects.create(
                    user=user,
                    subject=rnd.choice(["DBMS", "OS", "CN", "DSA"]),
                    minutes=rnd.choice([25, 25, 50, 15]),
                    created_at=now - timedelta(
                        days=i,
                        hours=rnd.randint(0, 8),
                    ),
                )

    # Sample study notes
    note_data = [
        (
            "Normalization",
            "DBMS",
            "# Normalization\n"
            "- **1NF**: atomic values only\n"
            "- **2NF**: no partial dependency\n"
            "- **3NF**: no transitive dependency\n\n"
            "BCNF: every determinant must be a candidate key. "
            "Normalization reduces redundancy and improves data integrity.",
            "exam, unit-3",
            True,
            True,
        ),
        (
            "Process Scheduling",
            "OS",
            "FCFS: First come first served. "
            "SJF: Shortest job first gives minimum average waiting time. "
            "Round Robin: each process gets a fixed time quantum. "
            "Priority scheduling can cause starvation, solved by aging.",
            "exam",
            False,
            False,
        ),
        (
            "OSI Model",
            "CN",
            "Physical: moves raw bits. "
            "Data Link: framing and MAC addressing. "
            "Network: routing and IP addressing. "
            "Transport: end to end delivery using TCP or UDP. "
            "Application: user facing protocols like HTTP.",
            "revision",
            True,
            False,
        ),
    ]

    for title, subj, content, tags, important, pinned in note_data:
        StudyNote.objects.create(
            user=user,
            title=title,
            subject=subj,
            content=content,
            tags=tags,
            is_important=important,
            is_pinned=pinned,
        )

    # Sample flashcards
    flashcards = [
        (
            "What is a primary key?",
            "A column that uniquely identifies each row.",
            "DBMS",
        ),
        (
            "What is deadlock?",
            "Processes waiting forever for resources held by each other.",
            "OS",
        ),
        (
            "TCP vs UDP?",
            "TCP is reliable and connection oriented; UDP is fast and connectionless.",
            "CN",
        ),
        (
            "What is a stack?",
            "A LIFO data structure.",
            "DSA",
        ),
    ]

    for question, answer, subject in flashcards:
        Flashcard.objects.create(
            user=user,
            subject=subject,
            question=question,
            answer=answer,
        )

    # Sample exams
    Exam.objects.create(
        user=user,
        name="DBMS Mid-Sem",
        subject="DBMS",
        exam_date=today + timedelta(days=9),
    )

    Exam.objects.create(
        user=user,
        name="Operating Systems",
        subject="OS",
        exam_date=today + timedelta(days=16),
    )

    Exam.objects.create(
        user=user,
        name="Computer Networks",
        subject="CN",
        exam_date=today + timedelta(days=24),
    )

    # Sample syllabus
    syllabus_data = [
        (
            "DBMS",
            [
                "ER Model",
                "Relational Algebra",
                "SQL",
                "Normalization",
                "Transactions",
            ],
            3,
        ),
        (
            "OS",
            [
                "Processes",
                "Scheduling",
                "Memory Management",
                "File Systems",
            ],
            2,
        ),
        (
            "CN",
            [
                "Physical Layer",
                "Data Link",
                "Network Layer",
                "Transport Layer",
            ],
            1,
        ),
    ]

    for name, chapters, completed_count in syllabus_data:
        syllabus = SyllabusSubject.objects.create(
            user=user,
            name=name,
        )

        for i, title in enumerate(chapters):
            Chapter.objects.create(
                subject=syllabus,
                title=title,
                order=i,
                done=i < completed_count,
            )

    # Sample timetable
    timetable_data = [
        (0, 9, 10, "DBMS Lecture", "class"),
        (0, 17, 19, "Self study: DSA", "study"),
        (1, 10, 11, "OS Lecture", "class"),
        (2, 9, 10, "CN Lecture", "class"),
        (2, 16, 18, "Lab: SQL", "class"),
        (3, 18, 20, "Revision", "study"),
        (4, 11, 12, "DSA Lecture", "class"),
        (5, 10, 13, "Mock test", "study"),
    ]

    for day, start, end, title, kind in timetable_data:
        TimetableSlot.objects.create(
            user=user,
            day=day,
            start_time=time(start),
            end_time=time(end),
            title=title,
            kind=kind,
        )

    # Create sample PYQs owned only by the demo account.
    ensure_demo_pyqs(user)

    return user

from django.urls import NoReverseMatch, reverse

NAV = [
    ("Overview", [
        ("🏠", "Dashboard", "dashboard"),
        ("🏆", "Achievements", "hub:achievements"),
    ]),
    ("Plan", [
        ("🗓️", "Planner", "planner:list"),
        ("🧩", "Board", "planner:board"),
        ("📅", "Calendar", "hub:calendar"),
        ("⏱️", "Focus Timer", "hub:focus"),
        ("🎯", "Goals", "planner:goals"),
        ("🕒", "Timetable", "hub:timetable"),
        ("🎓", "Exams", "hub:exams"),
    ]),
    ("Learn", [
        ("📝", "Notes", "study_notes:list"),
        ("📖", "Syllabus", "hub:syllabus"),
        ("🃏", "Flashcards", "hub:flashcards"),
        ("📚", "PYQs", "pyq:list"),
        ("📊", "PYQ Analytics", "pyq:analytics"),
        ("🤖", "AI Assistant", "hub:ai"),
    ]),
]


def shell(request):
    """Data used by the sidebar shown on every logged-in page."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    from . import services

    path = request.path
    groups = []
    for title, items in NAV:
        rows = []
        for icon, label, name in items:
            try:
                url = reverse(name)
            except NoReverseMatch:
                continue
            active = path == url if name in ("dashboard", "planner:list", "pyq:list", "study_notes:list") else path.startswith(url)
            rows.append({"icon": icon, "label": label, "url": url, "active": active})
        groups.append({"title": title, "items": rows})

    profile = getattr(user, "student_profile", None)
    avatar_url = ""
    if profile and profile.avatar:
        try:
            avatar_url = profile.avatar.url
        except Exception:
            avatar_url = ""
    name = user.first_name or user.username
    return {
        "nav_groups": groups,
        "side_user": {"name": name, "initial": name[:1].upper(), "avatar": avatar_url},
        "side_level": services.get_level_info(user),
    }

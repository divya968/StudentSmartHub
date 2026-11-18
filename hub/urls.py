from django.urls import path

from . import views

app_name = "hub"

urlpatterns = [
    path("achievements/", views.achievements, name="achievements"),
    path("achievements/freeze/", views.freeze_use, name="freeze"),
    path("focus/", views.focus, name="focus"),
    path("focus/log/", views.focus_log, name="focus_log"),
    path("exams/", views.exams, name="exams"),
    path("exams/delete/<int:pk>/", views.exam_delete, name="exam_delete"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("syllabus/", views.syllabus, name="syllabus"),
    path("syllabus/subject/add/", views.syllabus_add_subject, name="syllabus_add"),
    path("syllabus/subject/<int:pk>/delete/", views.syllabus_delete_subject, name="syllabus_delete"),
    path("syllabus/subject/<int:pk>/chapters/", views.chapter_add, name="chapter_add"),
    path("syllabus/chapter/<int:pk>/toggle/", views.chapter_toggle, name="chapter_toggle"),
    path("syllabus/chapter/<int:pk>/delete/", views.chapter_delete, name="chapter_delete"),
    path("flashcards/", views.flashcards, name="flashcards"),
    path("flashcards/study/", views.flashcard_study, name="flashcard_study"),
    path("flashcards/<int:pk>/mark/", views.flashcard_mark, name="flashcard_mark"),
    path("flashcards/<int:pk>/delete/", views.flashcard_delete, name="flashcard_delete"),
    path("flashcards/from-note/<int:pk>/", views.flashcards_from_note, name="flashcards_from_note"),
    path("timetable/", views.timetable, name="timetable"),
    path("timetable/delete/<int:pk>/", views.slot_delete, name="slot_delete"),
    path("ai/", views.ai_page, name="ai"),
    path("ai/summary/", views.ai_summary, name="ai_summary"),
    path("ai/quiz/", views.ai_quiz, name="ai_quiz"),
    path("ai/chat/", views.ai_chat, name="ai_chat"),
    path("ai/predict/", views.ai_predict, name="ai_predict"),
    path("search/", views.search, name="search"),
    path("export/<str:kind>/<str:fmt>/", views.export_data, name="export"),
]

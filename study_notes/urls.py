from django.urls import path
from . import views

app_name = "study_notes"

urlpatterns = [
    path("", views.note_list, name="list"),
    path("add/", views.note_create, name="add"),
    path("edit/<int:pk>/", views.note_edit, name="edit"),
    path("delete/<int:pk>/", views.note_delete, name="delete"),
    path("important/<int:pk>/", views.note_important, name="important"),
]

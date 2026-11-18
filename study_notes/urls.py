from django.urls import path
from . import views

app_name = "study_notes"

urlpatterns = [
    path("", views.note_list, name="list"),
    path("add/", views.note_create, name="add"),
    path("edit/<int:pk>/", views.note_edit, name="edit"),
    path("delete/<int:pk>/", views.note_delete, name="delete"),
    path("view/<int:pk>/", views.note_detail, name="detail"),
    path("pin/<int:pk>/", views.note_pin, name="pin"),
    path("export/<int:pk>/<str:fmt>/", views.note_export, name="export"),
    path("important/<int:pk>/", views.note_important, name="important"),
]

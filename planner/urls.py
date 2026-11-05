from django.urls import path
from . import views

app_name = "planner"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("add/", views.task_create, name="add"),
    path("edit/<int:pk>/", views.task_edit, name="edit"),
    path("delete/<int:pk>/", views.task_delete, name="delete"),
    path("toggle/<int:pk>/", views.task_toggle, name="toggle"),
    path("checkin/", views.study_checkin, name="checkin"),
    path("goals/", views.study_goal_view, name="goals"),
]


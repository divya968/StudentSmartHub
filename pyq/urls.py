from django.urls import path
from . import views

app_name = "pyq"

urlpatterns = [
    path("", views.pyq_list, name="list"),
    path("add/", views.pyq_add, name="add"),
    path("edit/<int:pk>/", views.pyq_edit, name="edit"),
    path("delete/<int:pk>/", views.pyq_delete, name="delete"),
    path('upload/', views.pyq_upload, name='upload'),
    path("preview/<int:pk>/", views.pyq_preview, name="preview"),
    path("repeated/", views.repeated_questions, name="repeated"),
    path("analytics/", views.pyq_analytics, name="analytics"),
]





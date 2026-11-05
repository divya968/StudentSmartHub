from django import forms
from .models import StudyTask

class StudyTaskForm(forms.ModelForm):
    class Meta:
        model = StudyTask
        fields = ["title", "subject", "description", "due_date", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Enter task name"}),
            "subject": forms.TextInput(attrs={"placeholder": "e.g. Python, DBMS"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Task details..."}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "priority": forms.Select(),
        }

from .models import StudyGoal


class StudyGoalForm(forms.ModelForm):
    class Meta:
        model = StudyGoal
        fields = ["target_hours", "studied_hours", "target_tasks"]
        widgets = {
            "target_hours": forms.NumberInput(attrs={
                "step": "0.5",
                "min": "0.5",
                "placeholder": "e.g. 4"
            }),
            "studied_hours": forms.NumberInput(attrs={
                "step": "0.5",
                "min": "0",
                "max": "24",
                "placeholder": "e.g. 3.5"
            }),
            "target_tasks": forms.NumberInput(attrs={
                "min": "1",
                "placeholder": "e.g. 5"
            }),
        }

    def clean_target_hours(self):
        hours = self.cleaned_data["target_hours"]

        if hours <= 0 or hours > 24:
            raise forms.ValidationError(
                "Study hours must be greater than 0 and at most 24."
            )

        return hours

    def clean_studied_hours(self):
        hours = self.cleaned_data["studied_hours"]

        if hours < 0 or hours > 24:
            raise forms.ValidationError("Studied hours must be between 0 and 24.")

        return hours

    def clean_target_tasks(self):
        tasks = self.cleaned_data["target_tasks"]

        if tasks < 1:
            raise forms.ValidationError(
                "Target tasks must be at least 1."
            )

        return tasks


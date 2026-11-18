from django import forms

from .models import Exam, Flashcard, TimetableSlot


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["name", "subject", "exam_date"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. DBMS Mid-Sem"}),
            "subject": forms.TextInput(attrs={"placeholder": "Subject (optional)"}),
            "exam_date": forms.DateInput(attrs={"type": "date"}),
        }


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ["subject", "question", "answer"]
        widgets = {
            "subject": forms.TextInput(attrs={"placeholder": "Subject"}),
            "question": forms.Textarea(attrs={"rows": 2, "placeholder": "Question / term"}),
            "answer": forms.Textarea(attrs={"rows": 2, "placeholder": "Answer / definition"}),
        }


class TimetableSlotForm(forms.ModelForm):
    class Meta:
        model = TimetableSlot
        fields = ["day", "start_time", "end_time", "title", "kind"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "title": forms.TextInput(attrs={"placeholder": "e.g. DBMS Lecture"}),
        }

    def clean(self):
        data = super().clean()
        if data.get("start_time") and data.get("end_time") and data["end_time"] <= data["start_time"]:
            raise forms.ValidationError("End time must be after start time.")
        return data

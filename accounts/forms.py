from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile


class StudentRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, label="Full Name")
    email = forms.EmailField()
    course = forms.CharField(max_length=100)
    semester = forms.ChoiceField(choices=StudentProfile.SEMESTER_CHOICES)

    class Meta:
        model = User
        fields = [
            "username", "full_name", "email",
            "course", "semester", "password1", "password2"
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)

        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.email = self.cleaned_data["email"].lower()

        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                course=self.cleaned_data["course"],
                semester=self.cleaned_data["semester"]
            )
        return user

class StudentProfileUpdateForm(forms.Form):
    full_name = forms.CharField(max_length=150, label="Full Name")
    email = forms.EmailField()
    course = forms.CharField(max_length=100)
    semester = forms.ChoiceField(choices=StudentProfile.SEMESTER_CHOICES)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user:
            self.fields["full_name"].initial = user.get_full_name()
            self.fields["email"].initial = user.email
            self.fields["course"].initial = user.student_profile.course
            self.fields["semester"].initial = user.student_profile.semester

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email__iexact=email).exclude(
            pk=self.user.pk
        ).exists():
            raise forms.ValidationError("This email is already registered.")

        return email

    def save(self):
        user = self.user
        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)

        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.email = self.cleaned_data["email"].lower()
        user.save()

        profile = user.student_profile
        profile.course = self.cleaned_data["course"]
        profile.semester = self.cleaned_data["semester"]
        profile.save()

        return user

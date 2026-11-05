from django import forms
from .models import StudyNote


class StudyNoteForm(forms.ModelForm):
    class Meta:
        model = StudyNote
        fields = ['title', 'subject', 'content', 'attachment', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter note title'}),
            'subject': forms.TextInput(attrs={'placeholder': 'Enter subject'}),
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Write your notes here...'}),
            'attachment': forms.ClearableFileInput(attrs={
                'accept': '.pdf,.docx,.txt'
            }),
        }

    def clean_attachment(self):
        uploaded_file = self.cleaned_data.get('attachment')

        if uploaded_file:
            import os
            extension = os.path.splitext(uploaded_file.name)[1].lower()

            if extension not in ['.pdf', '.docx', '.txt']:
                raise forms.ValidationError(
                    'Only PDF, DOCX and TXT files are allowed.'
                )

            if uploaded_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(
                    'File size must be less than 10 MB.'
                )

        return uploaded_file

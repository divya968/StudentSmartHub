from django import forms
from .models import PYQuestion, PYQUpload


class PYQuestionForm(forms.ModelForm):
    class Meta:
        model = PYQuestion
        fields = [
            'subject',
            'topic',
            'question',
            'year',
            'exam_name',
            'marks',
            'is_important',
        ]

        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': 'Enter subject name'}),
            'topic': forms.TextInput(attrs={'placeholder': 'Enter topic'}),
            'question': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter question'}),
            'year': forms.NumberInput(attrs={'placeholder': 'e.g. 2024'}),
            'exam_name': forms.TextInput(attrs={'placeholder': 'Enter exam name'}),
            'marks': forms.NumberInput(attrs={'placeholder': 'Enter marks'}),
        }


class PYQUploadForm(forms.ModelForm):
    class Meta:
        model = PYQUpload
        fields = ['file']

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
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


class PYQPreviewForm(forms.Form):
    subject = forms.CharField(max_length=100)
    topic = forms.CharField(max_length=150, initial='General')
    year = forms.IntegerField(min_value=1900, max_value=2100)
    exam_name = forms.CharField(max_length=150, required=False)
    questions = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': 'Extracted questions will appear here...'
        })
    )

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import PYQUpload
from .pdf_utils import split_questions


class QuestionSplittingTests(TestCase):
    def test_splits_numbered_questions_and_keeps_wrapped_lines(self):
        text = (
            "Q1. Explain the first concept in detail.\n"
            "Include one suitable example.\n"
            "2) Describe the second concept with a diagram.\n"
            "3. Write short notes on the third topic."
        )
        questions = split_questions(text)
        self.assertEqual(len(questions), 3)
        self.assertIn("Include one suitable example", questions[0])
        self.assertTrue(questions[1].startswith("Describe the second"))

    def test_falls_back_to_question_mark_paragraphs(self):
        text = "What is a compiler and why is it needed?\n\nHow does an interpreter work?"
        self.assertEqual(len(split_questions(text)), 2)


@override_settings(MEDIA_ROOT='/tmp/student_smarthub_pyq_test_media')
class UploadedPDFDeletionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='pyq-test-user', password='StrongTestPassword123!'
        )
        self.client.force_login(self.user)
        self.upload = PYQUpload.objects.create(
            user=self.user,
            file=SimpleUploadedFile('paper.pdf', b'%PDF-1.4 test content', content_type='application/pdf'),
            file_name='paper.pdf',
        )

    def test_owner_can_delete_uploaded_pdf(self):
        response = self.client.post(reverse('pyq:upload_delete', args=[self.upload.pk]))
        self.assertRedirects(response, reverse('pyq:upload'))
        self.assertFalse(PYQUpload.objects.filter(pk=self.upload.pk).exists())

    def test_other_user_cannot_delete_uploaded_pdf(self):
        other = get_user_model().objects.create_user(
            username='other-pyq-user', password='StrongTestPassword123!'
        )
        self.client.force_login(other)
        response = self.client.post(reverse('pyq:upload_delete', args=[self.upload.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PYQUpload.objects.filter(pk=self.upload.pk).exists())


    def test_locked_file_keeps_upload_record_and_shows_message(self):
        from unittest.mock import patch
        from django.contrib.messages import get_messages

        with patch('django.core.files.storage.FileSystemStorage.delete', side_effect=PermissionError("file is locked")):
            response = self.client.post(reverse('pyq:upload_delete', args=[self.upload.pk]))

        self.assertRedirects(response, reverse('pyq:upload'))
        self.assertTrue(PYQUpload.objects.filter(pk=self.upload.pk).exists())
        self.assertTrue(any('Windows is still using this PDF' in str(m) for m in get_messages(response.wsgi_request)))

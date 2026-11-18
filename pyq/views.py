
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import PYQuestion, PYQUpload
from .forms import PYQuestionForm, PYQUploadForm, PYQPreviewForm
from .pdf_utils import extract_pdf_text, split_questions, PDFExtractionError


@login_required
def pyq_list(request):
    questions = PYQuestion.objects.filter(user=request.user)

    query = request.GET.get('q', '').strip()
    subject = request.GET.get('subject', '').strip()

    if query:
        questions = questions.filter(
            question__icontains=query
        ) | questions.filter(
            subject__icontains=query
        ) | questions.filter(
            topic__icontains=query
        )

    if subject:
        questions = questions.filter(subject__iexact=subject)

    subjects = (
        PYQuestion.objects
        .filter(user=request.user)
        .values_list('subject', flat=True)
        .distinct()
    )

    return render(request, 'pyq/pyq_list.html', {
        'questions': questions,
        'subjects': subjects,
        'query': query,
        'selected_subject': subject,
    })


@login_required
def pyq_add(request):
    form = PYQuestionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        question = form.save(commit=False)
        question.user = request.user
        question.save()
        messages.success(request, 'PYQ question added successfully!')
        return redirect('pyq:list')

    return render(request, 'pyq/pyq_form.html', {
        'form': form,
    })


@login_required
def repeated_questions(request):
    user_questions = PYQuestion.objects.filter(user=request.user)

    groups = user_questions.values(
        'subject', 'question'
    ).annotate(
        repeat_count=Count('year', distinct=True)
    ).filter(
        repeat_count__gt=1
    ).order_by('-repeat_count')

    repeated = []

    for group in groups:
        group['years'] = list(
            user_questions.filter(
                subject=group['subject'],
                question=group['question']
            ).values_list('year', flat=True)
            .distinct()
            .order_by('year')
        )
        repeated.append(group)

    return render(request, 'pyq/repeated_questions.html', {
        'repeated_questions': repeated,
    })


@login_required
def pyq_upload(request):
    uploads = PYQUpload.objects.filter(
        user=request.user
    ).order_by('-uploaded_at')

    if request.method == 'POST':
        form = PYQUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            upload = form.save(commit=False)
            upload.user = request.user
            upload.file_name = uploaded_file.name
            upload.save()
            messages.success(request, 'PDF uploaded successfully!')
            return redirect('pyq:upload')
    else:
        form = PYQUploadForm()

    return render(request, 'pyq/pyq_upload.html', {
        'form': form,
        'uploads': uploads,
    })


@login_required
def pyq_preview(request, pk):
    upload = get_object_or_404(
        PYQUpload,
        pk=pk,
        user=request.user
    )

    if not upload.file.name.lower().endswith('.pdf'):
        return render(request, 'pyq/pyq_preview.html', {
            'error': 'Automatic extraction currently supports PDF files only.'
        })

    try:
        extracted_text = extract_pdf_text(upload.file)
        questions = split_questions(extracted_text)
    except PDFExtractionError as error:
        return render(request, 'pyq/pyq_preview.html', {
            'error': str(error),
            'upload': upload,
        })
    except Exception:
        return render(request, 'pyq/pyq_preview.html', {
            'error': 'This PDF could not be processed. Please try another PDF.',
            'upload': upload,
        })

    if not questions and request.method != 'POST':
        return render(request, 'pyq/pyq_preview.html', {
            'error': 'No questions could be detected automatically. You can still add questions manually from the PYQ page.',
            'upload': upload,
        })

    if request.method == 'POST':
        form = PYQPreviewForm(request.POST)

        if form.is_valid():
            question_list = [
                q.strip()
                for q in form.cleaned_data['questions'].splitlines()
                if q.strip()
            ]

            if not question_list:
                form.add_error(
                    'questions',
                    'Add at least one question before saving.'
                )
            else:
                for question in question_list:
                    PYQuestion.objects.create(
                        user=request.user,
                        subject=form.cleaned_data['subject'],
                        topic=form.cleaned_data['topic'],
                        question=question,
                        year=form.cleaned_data['year'],
                        exam_name=form.cleaned_data['exam_name']
                    )

                upload.is_processed = True
                upload.save(update_fields=['is_processed'])

                messages.success(
                    request,
                    f'{len(question_list)} question(s) saved. '
                    'Your original PDF is still available in My Uploaded Files.'
                )
                return redirect('pyq:list')
    else:
        form = PYQPreviewForm(initial={
            'subject': '',
            'topic': 'General',
            'year': '',
            'exam_name': '',
            'questions': '\n'.join(questions),
        })

    return render(request, 'pyq/pyq_preview.html', {
        'form': form,
        'upload': upload,
        'question_count': len(questions),
    })


@login_required
def pyq_analytics(request):
    user_questions = PYQuestion.objects.filter(user=request.user)

    total_questions = user_questions.count()

    important_questions = user_questions.filter(
        is_important=True
    ).count()

    repeated_count = user_questions.values(
        'subject', 'question'
    ).annotate(
        repeat_count=Count('year', distinct=True)
    ).filter(
        repeat_count__gt=1
    ).count()

    subject_stats = list(
        user_questions.values('subject')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    year_stats = list(
        user_questions.values('year')
        .annotate(total=Count('id'))
        .order_by('year')
    )

    context = {
        'total_questions': total_questions,
        'important_questions': important_questions,
        'repeated_count': repeated_count,
        'subject_stats': subject_stats,
        'year_stats': year_stats,
    }

    return render(request, 'pyq/analytics.html', context)


@login_required
def pyq_edit(request, pk):
    question = get_object_or_404(
        PYQuestion,
        pk=pk,
        user=request.user
    )

    form = PYQuestionForm(
        request.POST or None,
        instance=question
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'PYQ question updated.')
        return redirect('pyq:list')

    return render(request, 'pyq/pyq_form.html', {
        'form': form,
        'heading': 'Edit PYQ Question',
    })


@login_required
def pyq_delete(request, pk):
    question = get_object_or_404(
        PYQuestion,
        pk=pk,
        user=request.user
    )

    if request.method == 'POST':
        question.delete()
        messages.success(request, 'PYQ question deleted.')

    return redirect('pyq:list')


@login_required
@require_POST
def pyq_upload_delete(request, pk):
    upload = get_object_or_404(
        PYQUpload,
        pk=pk,
        user=request.user
    )

    if upload.file:
        try:
            upload.file.close()
            upload.file.delete(save=False)
        except PermissionError:
            messages.error(
                request,
                'Windows is still using this PDF. Close it in your PDF viewer '
                'or any other program, then try deleting it again.'
            )
            return redirect('pyq:upload')

    upload.delete()
    messages.success(
        request,
        'Uploaded PDF deleted. Saved PYQ questions were not changed.'
    )
    return redirect('pyq:upload')


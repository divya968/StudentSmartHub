from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from .models import PYQuestion, PYQUpload
from .forms import PYQuestionForm, PYQUploadForm, PYQPreviewForm
from .pdf_utils import extract_pdf_text, split_questions


@login_required
def pyq_list(request):
    questions = PYQuestion.objects.all()

    query = request.GET.get('q', '').strip()
    subject = request.GET.get('subject', '').strip()

    if query:
        questions = questions.filter(
            Q(question__icontains=query) |
            Q(subject__icontains=query) |
            Q(topic__icontains=query)
        )

    if subject:
        questions = questions.filter(subject__iexact=subject)

    subjects = PYQuestion.objects.values_list(
        'subject', flat=True
    ).distinct()

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
        form.save()
        return redirect('pyq:list')

    return render(request, 'pyq/pyq_form.html', {
        'form': form,
    })


@login_required
def repeated_questions(request):
    groups = PYQuestion.objects.values(
        'subject', 'question'
    ).annotate(
        repeat_count=Count('year', distinct=True)
    ).filter(
        repeat_count__gt=1
    ).order_by('-repeat_count')

    repeated = []

    for group in groups:
        group['years'] = list(
            PYQuestion.objects.filter(
                subject=group['subject'],
                question=group['question']
            ).values_list('year', flat=True).distinct().order_by('year')
        )
        repeated.append(group)

    return render(request, 'pyq/repeated_questions.html', {
        'repeated_questions': repeated,
    })



@login_required
def pyq_upload(request):
    uploads = PYQUpload.objects.filter(user=request.user).order_by('-uploaded_at')

    if request.method == 'POST':
        form = PYQUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            upload = form.save(commit=False)
            upload.user = request.user
            upload.file_name = uploaded_file.name
            upload.save()
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
    except Exception as error:
        return render(request, 'pyq/pyq_preview.html', {
            'error': f'PDF could not be read: {error}'
        })

    if request.method == 'POST':
        form = PYQPreviewForm(request.POST)

        if form.is_valid():
            question_list = [
                q.strip()
                for q in form.cleaned_data['questions'].splitlines()
                if q.strip()
            ]

            for question in question_list:
                PYQuestion.objects.create(
                    subject=form.cleaned_data['subject'],
                    topic=form.cleaned_data['topic'],
                    question=question,
                    year=form.cleaned_data['year'],
                    exam_name=form.cleaned_data['exam_name']
                )

            upload.is_processed = True
            upload.save()

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
    total_questions = PYQuestion.objects.count()

    important_questions = PYQuestion.objects.filter(
        is_important=True
    ).count()

    repeated_count = PYQuestion.objects.values(
        'subject', 'question'
    ).annotate(
        repeat_count=Count('year', distinct=True)
    ).filter(
        repeat_count__gt=1
    ).count()

    subject_stats = list(
        PYQuestion.objects.values('subject')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    year_stats = list(
        PYQuestion.objects.values('year')
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
def pyq_analytics(request):
    total_questions = PYQuestion.objects.count()

    important_questions = PYQuestion.objects.filter(
        is_important=True
    ).count()

    repeated_count = PYQuestion.objects.values(
        'subject', 'question'
    ).annotate(
        repeat_count=Count('year', distinct=True)
    ).filter(
        repeat_count__gt=1
    ).count()

    subject_stats = list(
        PYQuestion.objects.values('subject')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    year_stats = list(
        PYQuestion.objects.values('year')
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
    question = get_object_or_404(PYQuestion, pk=pk)

    form = PYQuestionForm(
        request.POST or None,
        instance=question
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('pyq:list')

    return render(request, 'pyq/pyq_form.html', {
        'form': form,
        'heading': 'Edit PYQ Question',
    })


@login_required
def pyq_delete(request, pk):
    question = get_object_or_404(PYQuestion, pk=pk)

    if request.method == 'POST':
        question.delete()

    return redirect('pyq:list')

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import StudyNote
from .forms import StudyNoteForm


@login_required
def note_list(request):
    notes = StudyNote.objects.filter(user=request.user)
    query = request.GET.get('q', '').strip()

    if query:
        notes = notes.filter(
            Q(title__icontains=query) |
            Q(subject__icontains=query) |
            Q(content__icontains=query)
        )

    tag = request.GET.get('tag', '').strip()
    subject = request.GET.get('subject', '').strip()
    all_notes = StudyNote.objects.filter(user=request.user)
    all_tags = sorted({t for n in all_notes for t in n.tag_list})
    all_subjects = sorted({n.subject for n in all_notes if n.subject})
    if subject:
        notes = notes.filter(subject__iexact=subject)
    if tag:
        notes = notes.filter(tags__icontains=tag)

    return render(request, 'study_notes/note_list.html', {
        'notes': notes,
        'query': query,
        'tag': tag,
        'subject': subject,
        'all_tags': all_tags,
        'all_subjects': all_subjects,
    })


@login_required
def note_create(request):
    form = StudyNoteForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == 'POST' and form.is_valid():
        note = form.save(commit=False)
        note.user = request.user
        note.save()
        messages.success(request, 'Note saved! 📝 +5 XP')
        return redirect('study_notes:list')

    return render(request, 'study_notes/note_form.html', {
        'form': form,
        'heading': 'Create New Note',
    })


@login_required
def note_edit(request, pk):
    note = get_object_or_404(StudyNote, pk=pk, user=request.user)

    form = StudyNoteForm(
        request.POST or None,
        request.FILES or None,
        instance=note
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Note updated.')
        return redirect('study_notes:list')

    return render(request, 'study_notes/note_form.html', {
        'form': form,
        'heading': 'Edit Note',
    })


@login_required
def note_delete(request, pk):
    note = get_object_or_404(StudyNote, pk=pk, user=request.user)

    if request.method == 'POST':
        note.delete()

    return redirect('study_notes:list')


@login_required
def note_important(request, pk):
    note = get_object_or_404(StudyNote, pk=pk, user=request.user)

    if request.method == 'POST':
        note.is_important = not note.is_important
        note.save()

    return redirect('study_notes:list')


@login_required
def note_detail(request, pk):
    note = get_object_or_404(StudyNote, pk=pk, user=request.user)
    return render(request, 'study_notes/note_detail.html', {'note': note})


@login_required
def note_pin(request, pk):
    note = get_object_or_404(StudyNote, pk=pk, user=request.user)

    if request.method == 'POST':
        note.is_pinned = not note.is_pinned
        note.save()
        messages.success(request, 'Note pinned to top 📌' if note.is_pinned else 'Note unpinned.')

    return redirect(request.POST.get('next') or 'study_notes:list')


@login_required
def note_export(request, pk, fmt):
    from django.http import Http404
    from hub.exports import build_note_pdf

    note = get_object_or_404(StudyNote, pk=pk, user=request.user)
    safe = ''.join(c if c.isalnum() else '_' for c in note.title)[:40] or 'note'

    if fmt == 'pdf':
        resp = HttpResponse(build_note_pdf(note), content_type='application/pdf')
    elif fmt in ('md', 'txt'):
        body = f"# {note.title}\n\nSubject: {note.subject}\nTags: {note.tags}\n\n{note.content}\n"
        resp = HttpResponse(body, content_type='text/plain; charset=utf-8')
    else:
        raise Http404
    resp['Content-Disposition'] = f'attachment; filename="{safe}.{fmt}"'
    return resp

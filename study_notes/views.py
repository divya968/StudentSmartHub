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

    return render(request, 'study_notes/note_list.html', {
        'notes': notes,
        'query': query,
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

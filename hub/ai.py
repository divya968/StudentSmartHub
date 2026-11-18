"""Free, local study-assistant tools. No API key, paid service or internet call is used."""
import random
import re
from collections import Counter, defaultdict

MAX_INPUT_CHARS = 12000


def ai_available():
    """Return True because the built-in study tools work fully offline."""
    return True
STOPWORDS = set("""a an the and or but if then else of in on at to for from by with without about as is are was were be been being this that these those it its into over under than so such not no nor can could should would will shall may might must do does did have has had having he she they we you your their our his her them us also more most other some any each very just which who whom what when where why how all both few many much own same too only again further once here""".split())


def _clean_line(value):
    value = re.sub(r"^\s*(?:[-*•]+|\d+[.)]|[•▪◦])\s*", "", value)
    value = re.sub(r"[`*_#]+", "", value)
    return re.sub(r"\s+", " ", value).strip(" \t-–—")


def _sentences(text):
    text = re.sub(r"[*#`]", "", text or "")
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [_clean_line(p) for p in parts if len(p.split()) >= 4]


def _words(text):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z\-']+", (text or '').lower()) if w not in STOPWORDS and len(w) > 2]


def _keywords(text):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", text or '') if w.lower() not in STOPWORDS]


def _unique_units(text):
    """Preserve whole note lines/definitions; join wrapped continuation lines."""
    units, current = [], ""
    for raw in (text or "").splitlines():
        line = _clean_line(raw)
        if not line:
            if current:
                units.append(current); current = ""
            continue
        # Keep a definition/table row as a single unit. Join short wrapped lines.
        if current and len(line.split()) < 5 and not re.search(r"[:–—-]", line):
            current += " " + line
        else:
            if current: units.append(current)
            current = line
    if current: units.append(current)
    seen, result = set(), []
    for unit in units:
        key = re.sub(r"\W+", " ", unit.lower()).strip()
        if key and key not in seen and len(unit.split()) >= 4:
            seen.add(key); result.append(unit)
    return result


def summarize(text, sentences=5):
    text = (text or "")[:MAX_INPUT_CHARS]
    units = _unique_units(text)
    if len(units) < 2:
        units = _sentences(text)
    if not units:
        return {"text": "Add a little more study material (at least a few complete sentences) and try again.", "mode": "offline"}
    freq = Counter(w for unit in units for w in _words(unit))
    ranked = []
    for index, unit in enumerate(units):
        words = _words(unit)
        score = sum(freq[w] for w in words) / max(4, len(words))
        # Definitions and lines containing key relationships are useful revision points.
        if re.search(r"\b(is|are|means|refers to|defined as|consists of|used to|allows)\b|[:–—]", unit, re.I):
            score *= 1.18
        ranked.append((score, index, unit))
    count = max(1, min(int(sentences), 8))
    chosen = sorted(sorted(ranked, key=lambda x: (-x[0], x[1]))[:count], key=lambda x: x[1])
    return {"text": "\n".join(f"- {u}" for _, _, u in chosen), "mode": "offline"}


def _cloze_quiz(text, n, rng):
    sents = [s for s in _sentences(text) if 6 <= len(s.split()) <= 40]
    pool = list(dict.fromkeys(w for s in sents for w in _keywords(s)))
    quiz = []
    rng.shuffle(sents)
    for sentence in sents:
        kws = _keywords(sentence)
        if not kws: continue
        answer = max(kws, key=len)
        distractors = [w for w in pool if w.lower() != answer.lower()]
        rng.shuffle(distractors)
        fillers = [w for w in ["process", "system", "function", "variable", "method", "structure"] if w.lower() != answer.lower()]
        options = list(dict.fromkeys((distractors + fillers)[:3] + [answer]))
        rng.shuffle(options)
        quiz.append({"q": re.sub(re.escape(answer), "_____", sentence, count=1, flags=re.I),
                     "options": options, "answer": options.index(answer), "explain": sentence})
        if len(quiz) >= n: break
    return quiz


def make_quiz(text, n=5):
    text = (text or "")[:MAX_INPUT_CHARS]
    n = max(1, min(int(n), 10))
    return {"questions": _cloze_quiz(text, n, random.Random(len(text))), "mode": "offline"}


_TERM = re.compile(r"^\s*[-*•\d.)]*\s*([^:–—\-\n]{2,60}?)\s*[:–—-]\s+(.{6,})$")


def make_flashcards(text, limit=15):
    text = (text or "")[:MAX_INPUT_CHARS]
    cards = []
    for line in (text.splitlines()):
        m = _TERM.match(line)
        if m:
            cards.append((f"What is {m.group(1).strip()}?", m.group(2).strip()))
    if not cards:
        for item in _cloze_quiz(text, limit, random.Random(7)):
            cards.append((item["q"], item["options"][item["answer"]]))
    return {"cards": cards[:limit], "mode": "offline"}


def predict_pyq(queryset, limit=8):
    groups = defaultdict(list)
    for q in queryset:
        key = (q.subject.strip().lower(), q.topic.strip().lower())
        groups[key].append(q)
    if not groups: return []
    latest = max(q.year for items in groups.values() for q in items)
    rows = []
    for (subject, topic), items in groups.items():
        years = sorted({q.year for q in items})
        important = sum(1 for q in items if q.is_important)
        avg_marks = sum(q.marks for q in items) / len(items)
        gap = latest - years[-1]
        score = len(items)*3 + len(years)*2 + important*2 + min(avg_marks/5, 3) + (2 if gap >= 1 else 0)
        reasons = [f"asked {len(items)}x in {len(years)} year(s)"]
        if important: reasons.append("marked important")
        if gap >= 1: reasons.append(f"not seen since {years[-1]}")
        rows.append({"subject": items[0].subject, "topic": items[0].topic, "score": score,
                     "reason": ", ".join(reasons), "years": years})
    rows.sort(key=lambda r: -r["score"])
    top = rows[:limit]; best = top[0]["score"] or 1
    for row in top: row["priority"] = max(10, round(row["score"]*100/best))
    return top


def _search_notes(question, notes, k=4):
    q_words = set(_words(question))
    scored = []
    for note in notes:
        content = f"{note.title} {note.subject} {note.tags} {note.content}"
        hay = set(_words(content))
        overlap = len(q_words & hay)
        if overlap: scored.append((overlap, note))
    scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
    return [note for _, note in scored[:k]]


def chat(question, notes):
    question = (question or "").strip()[:1000]
    if not question:
        return {"answer": "Ask me a question about a subject or topic, and I'll look through your saved notes.", "mode": "offline", "sources": []}
    qlow = question.lower()
    if any(g in qlow for g in ("hello", "hi", "hey", "good morning", "good evening")) and len(question.split()) < 6:
        return {"answer": "Hey! 👋 I'm your free Study Buddy. Ask me to explain a topic, find a definition in your notes, make a quick revision plan, or quiz you. No subscription or API key needed.", "mode": "offline", "sources": []}
    related = _search_notes(question, notes)
    if not related:
        return {"answer": "I couldn't find a close match in your saved notes yet. Try adding the topic to Notes, or include the subject and a few keywords in your question. I won't make up an answer when I don't have reliable study material.", "mode": "offline", "sources": []}
    q_words = set(_words(question))
    extracts = []
    for note in related:
        units = _unique_units(note.content) or _sentences(note.content)
        ranked = sorted(((len(q_words & set(_words(unit))), idx, unit) for idx, unit in enumerate(units)), key=lambda x: (-x[0], x[1]))
        best = [unit for score, _, unit in ranked if score > 0][:4]
        if not best: best = units[:2]
        if best:
            extracts.append((note, best))
    if not extracts:
        return {"answer": "I found a related note, but it doesn't contain enough readable text to answer. Try adding a clearer explanation to that note.", "mode": "offline", "sources": [n.title for n in related]}
    parts = ["Here's what I found in your study material:\n"]
    for note, lines in extracts:
        parts.append(f"📘 {note.title} ({note.subject})\n" + "\n".join(f"• {line}" for line in lines))
    parts.append("\nQuick study tip: read the key idea once, close your notes, and try explaining it in your own words. Want me to turn this topic into a quiz? Open the ‘Quiz me’ tab.")
    return {"answer": "\n\n".join(parts), "mode": "offline", "sources": [n.title for n, _ in extracts]}

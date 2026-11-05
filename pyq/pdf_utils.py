import re
from pypdf import PdfReader


def extract_pdf_text(pdf_file):
    pdf_file.seek(0)
    reader = PdfReader(pdf_file)

    extracted_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            extracted_text.append(text)

    return "\n".join(extracted_text)


def split_questions(text):
    lines = text.splitlines()
    questions = []
    current_question = []

    pattern = re.compile(
        r'^\s*(?:Q(?:uestion)?\.?\s*)?\d{1,3}\s*[\).:-]\s*',
        re.IGNORECASE
    )

    for line in lines:
        line = line.strip()

        if not line:
            continue

        match = pattern.match(line)

        if match:
            if current_question:
                questions.append(" ".join(current_question))

            current_question = [line[match.end():].strip()]

        elif current_question:
            current_question.append(line)

    if current_question:
        questions.append(" ".join(current_question))

    return [
        question for question in questions
        if len(question) > 10
    ]

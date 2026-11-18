"""PDF text extraction helpers for PYQ uploads.

Read the uploaded file into memory and close the Django storage handle before
parsing. This is important on Windows, where an open handle prevents deletion.
Scanned/image-only PDFs use optional Tesseract OCR.
"""

import io
import re

from pypdf import PdfReader


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or contains no extractable text."""


def _read_pdf_bytes(pdf_file):
    """Return PDF bytes and ensure Django's FieldFile handle is closed."""
    try:
        if hasattr(pdf_file, "open") and hasattr(pdf_file, "close"):
            pdf_file.open("rb")
            try:
                return pdf_file.read()
            finally:
                pdf_file.close()

        # Support file-like objects supplied by tests or other callers.
        position = pdf_file.tell() if hasattr(pdf_file, "tell") else None
        pdf_file.seek(0)
        data = pdf_file.read()
        if position is not None:
            pdf_file.seek(position)
        return data
    except Exception as exc:
        raise PDFExtractionError(f"PDF could not be opened: {exc}") from exc


def _extract_with_ocr(pdf_bytes):
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise PDFExtractionError(
            "This PDF appears to be scanned. OCR support is not installed. "
            "Install the optional PyMuPDF and pytesseract packages and the "
            "Tesseract OCR application, then try again."
        ) from exc

    pages_text = []
    try:
        # Opening from bytes avoids keeping the uploaded media file locked.
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            for page in document:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                page_text = pytesseract.image_to_string(image, config="--psm 6")
                if page_text.strip():
                    pages_text.append(page_text)
    except Exception as exc:
        message = str(exc)
        if "tesseract" in message.lower() or "not found" in message.lower():
            raise PDFExtractionError(
                "OCR could not start because Tesseract is not installed or "
                "is not on PATH. Install Tesseract OCR and retry."
            ) from exc
        raise PDFExtractionError(f"OCR could not read this PDF: {message}") from exc

    return "\n".join(pages_text)


def extract_pdf_text(pdf_file):
    """Extract text from a PDF without leaving its uploaded file open."""
    pdf_bytes = _read_pdf_bytes(pdf_file)
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
        extracted_text = []
        for page in reader.pages:
            try:
                text = page.extract_text(extraction_mode="layout") or page.extract_text() or ""
            except TypeError:  # Compatibility with older pypdf versions.
                text = page.extract_text() or ""
            if text.strip():
                extracted_text.append(text)
        text = "\n".join(extracted_text).strip()
    except Exception as exc:
        raise PDFExtractionError(f"PDF could not be opened: {exc}") from exc

    # A tiny amount of text is usually a scanned cover page or image-only PDF.
    if len(re.sub(r"\s", "", text)) < 40:
        ocr_text = _extract_with_ocr(pdf_bytes)
        if len(re.sub(r"\s", "", ocr_text)) > len(re.sub(r"\s", "", text)):
            text = ocr_text.strip()

    if not text:
        raise PDFExtractionError(
            "No readable text was found. If this is a scanned PDF, install "
            "Tesseract OCR and try again, or use a clearer/searchable PDF."
        )
    return text


QUESTION_START = re.compile(
    r"^\s*(?:"
    r"Q(?:uestion)?\s*\.?\s*\d{1,3}(?:[\).:\-]\s*|\s+)|"
    r"\(?\s*\d{1,3}[\).:\-]\s*"
    r")\s*",
    re.IGNORECASE,
)


def split_questions(text):
    """Split common numbered-question layouts while retaining wrapped lines."""
    if not text:
        return []

    questions = []
    current = []
    for raw_line in text.replace("\r", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        match = QUESTION_START.match(line)
        if match:
            if current:
                questions.append(" ".join(current).strip())
            current = [line[match.end():].strip()]
        elif current:
            current.append(line)

    if current:
        questions.append(" ".join(current).strip())

    questions = [re.sub(r"\s+", " ", q).strip(" -\t") for q in questions]
    questions = [q for q in questions if len(q) > 10]

    if questions:
        return questions

    paragraphs = [
        re.sub(r"\s+", " ", part).strip()
        for part in re.split(r"\n\s*\n", text)
        if part.strip()
    ]
    question_like = [part for part in paragraphs if "?" in part and len(part) > 10]
    if question_like:
        return question_like

    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if len(line) > 25]

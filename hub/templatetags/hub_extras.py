
import re
import html

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown_lite")
def markdown_lite(value):
    """
    Lightweight Markdown renderer.
    Supports headings, lists, bold, italic and paragraphs.
    HTML input is escaped to prevent XSS.
    """

    if value is None:
        return ""

    text = html.escape(str(value))

    lines = text.splitlines()
    output = []
    in_list = False
    paragraph = []

    def inline_format(content):
        content = re.sub(
            r"\*\*(.+?)\*\*",
            r"<strong>\1</strong>",
            content
        )
        content = re.sub(
            r"(?<!\*)\*([^*]+)\*(?!\*)",
            r"<em>\1</em>",
            content
        )
        content = re.sub(
            r"`([^`]+)`",
            r"<code>\1</code>",
            content
        )
        return content

    def close_paragraph():
        nonlocal paragraph
        if paragraph:
            output.append(
                "<p>" + inline_format(" ".join(paragraph)) + "</p>"
            )
            paragraph = []

    def close_list():
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            close_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)

        if heading:
            close_paragraph()
            close_list()

            level = min(len(heading.group(1)) + 2, 6)
            content = inline_format(heading.group(2))

            output.append(
                f"<h{level}>{content}</h{level}>"
            )
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", stripped)

        if bullet:
            close_paragraph()

            if not in_list:
                output.append("<ul>")
                in_list = True

            output.append(
                "<li>" + inline_format(bullet.group(1)) + "</li>"
            )
            continue

        close_list()
        paragraph.append(stripped)

    close_paragraph()
    close_list()

    return mark_safe("\n".join(output))

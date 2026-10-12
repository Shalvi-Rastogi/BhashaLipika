# from bs4 import BeautifulSoup, Comment, Doctype


# IGNORED_TAGS = {
#     "script",
#     "style",
#     "code",
#     "pre"
# }


# def translate_html(html_content, translate_func, src_lang, tgt_lang):

#     soup = BeautifulSoup(html_content, "html.parser")

#     replacements = []

#     for element in soup.find_all(string=True):

#         # Ignore comments
#         if isinstance(element, Comment):
#             continue

#         # Ignore DOCTYPE
#         if isinstance(element, Doctype):
#             continue

#         parent = element.parent

#         if not parent:
#             continue

#         # Don't translate code-like content
#         if parent.name in IGNORED_TAGS:
#             continue

#         original_text = str(element)

#         # Keep whitespace exactly as it is
#         if not original_text.strip():
#             continue

#         try:

#             translated = translate_func(
#                 original_text,
#                 src_lang,
#                 tgt_lang
#             )

#             if translated:

#                 replacements.append({
#                     "original": original_text,
#                     "translated": translated,
#                 })

#         except Exception as e:

#             print(
#                 f"[HTML] Translation failed for "
#                 f"{original_text[:50]!r}: {e}"
#             )

#     # ------------------------------------------------
#     # IMPORTANT:
#     # Use ORIGINAL HTML as the base.
#     # Never use str(soup) here.
#     # ------------------------------------------------

#     translated_html = html_content

#     for replacement in replacements:

#         original = replacement["original"]
#         translated = replacement["translated"]

#         translated_html = translated_html.replace(
#             original,
#             translated,
#             1
#         )

#     return translated_html

import re


# HTML tags that should not be sent to the translation model
TAG_PATTERN = re.compile(
    r"<!--.*?-->|<![^>]*>|<[^>]+>",
    re.DOTALL
)

# NUMBER_PATTERN = re.compile(
#     r"""
#     (?<![\w])
#     (?:
#         \d+(?:[.,]\d+)*
#         |
#         ₹\s?\d+(?:[.,]\d+)*
#         |
#         \d+(?:[.,]\d+)*%
#     )
#     (?![\w])
#     """,
#     re.VERBOSE
# )

# def _protect_numbers(text):
#     """
#     Protect numeric values from translation.
#     """

#     numbers = []

#     def replace(match):
#         index = len(numbers)

#         numbers.append(match.group(0))

#         return f"⟦N{index}⟧"

#     protected_text = NUMBER_PATTERN.sub(
#         replace,
#         text
#     )

#     return protected_text, numbers

def _extract_tags_and_text(html_content):
    tags = []
    text_parts = []
    text_position = 0
    last_end = 0

    for match in TAG_PATTERN.finditer(html_content):
        text_before_tag = html_content[last_end:match.start()]
        text_parts.append(text_before_tag)
        text_position += len(text_before_tag)
        tags.append({
            "tag": match.group(0),
            "position": text_position
        })
        last_end = match.end()

    text_parts.append(html_content[last_end:])
    return "".join(text_parts), tags


def _word_boundaries(text):
    boundaries = [0]
    boundaries.extend(
        match.end()
        for match in re.finditer(r"\s+", text)
    )
    boundaries.append(len(text))
    return sorted(set(boundaries))


def _map_tag_position(source_position, source_text, translated_text):
    source_boundaries = _word_boundaries(source_text)
    translated_boundaries = _word_boundaries(translated_text)

    source_boundary_index = max(
        index
        for index, boundary in enumerate(source_boundaries)
        if boundary <= source_position
    )
    source_ratio = source_boundary_index / max(
        len(source_boundaries) - 1,
        1
    )
    translated_boundary_index = round(
        source_ratio * (len(translated_boundaries) - 1)
    )
    return translated_boundaries[translated_boundary_index]


def _restore_tags(translated_text, tags, source_text):
    grouped_tags = {}

    for tag_data in tags:
        position = _map_tag_position(
            tag_data["position"],
            source_text,
            translated_text
        )
        grouped_tags.setdefault(position, []).append(tag_data["tag"])

    result = []
    current_position = 0

    for position in sorted(grouped_tags):
        result.append(translated_text[current_position:position])
        result.extend(grouped_tags[position])
        current_position = position

    result.append(translated_text[current_position:])
    return "".join(result)


def translate_html(
    html_content,
    translate_func,
    src_lang,
    tgt_lang
):
    """
    Translate HTML while preserving HTML tags.

    The complete visible text is translated together to
    preserve sentence context. Original tags are then
    restored in their original order.
    """

    if not html_content or not html_content.strip():
        return html_content

    plain_text, tags = _extract_tags_and_text(html_content)

    if not plain_text.strip():
        return html_content

    try:
        translated_text = translate_func(
            plain_text,
            src_lang,
            tgt_lang
        )

    except Exception as error:
        print(f"[HTML] Translation failed: {error}")
        return html_content

    if not translated_text:
        return html_content

    return _restore_tags(translated_text, tags, plain_text)
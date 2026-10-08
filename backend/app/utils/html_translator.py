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
    """
    Separate HTML tags from visible text.

    Returns:
        plain_text:
            Complete text without HTML tags.

        tags:
            List containing each tag and its position
            in the plain text.
    """

    tags = []
    text_parts = []

    current_text_position = 0
    last_end = 0

    for match in TAG_PATTERN.finditer(html_content):

        # Text before this tag
        text_before_tag = html_content[last_end:match.start()]

        if text_before_tag:
            text_parts.append(text_before_tag)
            current_text_position += len(text_before_tag)

        tag = match.group(0)

        tags.append({
            "tag": tag,
            "position": current_text_position
        })

        last_end = match.end()

    # Remaining text after the final tag
    remaining_text = html_content[last_end:]

    if remaining_text:
        text_parts.append(remaining_text)
        current_text_position += len(remaining_text)

    plain_text = "".join(text_parts)

    return plain_text, tags


def _get_word_boundaries(text):
    """
    Returns character positions that are safe places
    to insert HTML tags.

    A tag should never be inserted in the middle of a word.
    """
    boundaries = [0]

    for match in re.finditer(r"\s+", text):
        boundaries.append(match.end())

    if len(text) not in boundaries:
        boundaries.append(len(text))

    return sorted(set(boundaries))


def _map_position_to_word_boundary(
    source_position,
    source_text,
    target_text
):
    """
    Maps a source HTML-tag position to the translated text,
    but always returns a safe word boundary.
    """

    source_boundaries = _get_word_boundaries(source_text)
    target_boundaries = _get_word_boundaries(target_text)

    if not source_boundaries:
        return 0

    if not target_boundaries:
        return 0

    # Find how many source words/boundaries occur before
    # the original tag.
    source_index = 0

    for i, boundary in enumerate(source_boundaries):
        if boundary <= source_position:
            source_index = i
        else:
            break

    # Preserve relative location.
    ratio = source_index / max(
        len(source_boundaries) - 1,
        1
    )

    target_index = round(
        ratio * (len(target_boundaries) - 1)
    )

    target_index = min(
        target_index,
        len(target_boundaries) - 1
    )

    return target_boundaries[target_index]

# def _restore_numbers(text, numbers):
#     """
#     Restore protected numeric values after translation.
#     """

#     for index, number in enumerate(numbers):

#         placeholder = f"⟦N{index}⟧"

#         text = text.replace(
#             placeholder,
#             number
#         )

#     return text

def _is_closing_tag(tag):
    """
    Returns True if the HTML tag is a closing tag.
    """
    return bool(
        re.match(
            r"</\s*[A-Za-z][^>]*>",
            tag
        )
    )


def _restore_tags(
    translated_text,
    tags,
    source_text
):
    """
    Restore original HTML tags into translated text.

    Rules:
    1. Tags are mapped only to word boundaries.
    2. Original tag ordering is preserved.
    3. Nested opening tags remain nested correctly.
    4. Nested closing tags remain in their original order.
    """

    if not tags:
        return translated_text

    insertions = []

    for original_index, tag_data in enumerate(tags):

        tag = tag_data["tag"]
        source_position = tag_data["position"]

        target_position = _map_position_to_word_boundary(
            source_position,
            source_text,
            translated_text
        )

        insertions.append({
            "position": target_position,
            "tag": tag,
            "original_index": original_index,
            "closing": _is_closing_tag(tag)
        })

    # --------------------------------------------------
    # Group tags by their translated position
    # --------------------------------------------------

    grouped = {}

    for insertion in insertions:
        position = insertion["position"]

        if position not in grouped:
            grouped[position] = []

        grouped[position].append(insertion)

    # --------------------------------------------------
    # Sort tags inside each position.
    #
    # We deliberately preserve the original HTML order.
    # --------------------------------------------------

    for position in grouped:
        grouped[position].sort(
            key=lambda item: item["original_index"]
        )

    # --------------------------------------------------
    # Build the final HTML from left to right.
    # This avoids the insertion-order reversal problem.
    # --------------------------------------------------

    result = []
    current_position = 0

    for position in sorted(grouped.keys()):

        # Add translated text before the tag position
        result.append(
            translated_text[
                current_position:position
            ]
        )

        # Add all tags at this position
        for insertion in grouped[position]:
            result.append(insertion["tag"])

        current_position = position

    # Add remaining translated text
    result.append(
        translated_text[current_position:]
    )

    return "".join(result)


def translate_html(
    html_content,
    translate_func,
    src_lang,
    tgt_lang
):
    """
    Translate HTML while preserving HTML tags.

    IMPORTANT:
    The complete visible text is translated in ONE
    translation request.

    HTML tags are removed temporarily, their positions
    are recorded, and then the original tags are
    inserted back into the translated text.
    """

    if not html_content or not html_content.strip():
        return html_content

    # --------------------------------------------------
    # STEP 1:
    # Separate HTML tags from complete text
    # --------------------------------------------------

    plain_text, tags = _extract_tags_and_text(
        html_content
    )

    if not plain_text.strip():
        return html_content

    print("\n[HTML TRANSLATION]")
    print("Original HTML:")
    print(html_content)

    print("\n[HTML PLAIN TEXT]")
    print(plain_text)

    print("\n[HTML TAG SPANS]")

    for tag in tags:
        print(
            repr(tag["tag"]),
            "at position",
            tag["position"]
        )

    # --------------------------------------------------
    # STEP 2:
    # Translate the COMPLETE text
    # --------------------------------------------------

    try:

        print("\n[HTML TEXT SENT TO TRANSLATOR]")
        print(plain_text)

        translated_text = translate_func(
            plain_text,
            src_lang,
            tgt_lang
        )

    except Exception as error:

        print(
            f"[HTML] Translation failed: {error}"
        )

        return html_content

    if not translated_text:
        return html_content

    print("\n[HTML TRANSLATED TEXT]")
    print(translated_text)

    # --------------------------------------------------
    # STEP 3:
    # Restore HTML tags using their spans
    # --------------------------------------------------

    translated_html = _restore_tags(
        translated_text,
        tags,
        plain_text
    )

    print("\n[HTML FINAL OUTPUT]")
    print(translated_html)

    return translated_html
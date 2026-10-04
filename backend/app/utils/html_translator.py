# from bs4 import BeautifulSoup, Comment, Doctype

# def translate_html(html_content, translate_func, src_lang, tgt_lang):

#     soup = BeautifulSoup(html_content, "html.parser")

#     ignored_tags = {"script", "style", "code", "pre"}

#     for element in soup.find_all(string=True):

#         if isinstance(element, (Comment, Doctype)):
#             continue

#         parent = element.parent

#         if parent and parent.name in ignored_tags:
#             continue

#         original_text = str(element)

#         if not original_text.strip():
#             continue

#         try:
#             translated = translate_func(
#                 original_text,
#                 src_lang,
#                 tgt_lang
#             )

#             if translated:
#                 element.replace_with(translated)

#         except Exception as e:
#             print(
#                 f"[HTML] Translation failed for "
#                 f"{original_text[:50]!r}: {e}"
#             )

#     translated_html = str(soup)

#     return translated_html

from bs4 import BeautifulSoup, Comment, Doctype


IGNORED_TAGS = {
    "script",
    "style",
    "code",
    "pre"
}


def translate_html(html_content, translate_func, src_lang, tgt_lang):

    soup = BeautifulSoup(html_content, "html.parser")

    replacements = []

    for element in soup.find_all(string=True):

        # Ignore comments
        if isinstance(element, Comment):
            continue

        # Ignore DOCTYPE
        if isinstance(element, Doctype):
            continue

        parent = element.parent

        if not parent:
            continue

        # Don't translate code-like content
        if parent.name in IGNORED_TAGS:
            continue

        original_text = str(element)

        # Keep whitespace exactly as it is
        if not original_text.strip():
            continue

        try:

            translated = translate_func(
                original_text,
                src_lang,
                tgt_lang
            )

            if translated:

                replacements.append({
                    "original": original_text,
                    "translated": translated,
                })

        except Exception as e:

            print(
                f"[HTML] Translation failed for "
                f"{original_text[:50]!r}: {e}"
            )

    # ------------------------------------------------
    # IMPORTANT:
    # Use ORIGINAL HTML as the base.
    # Never use str(soup) here.
    # ------------------------------------------------

    translated_html = html_content

    for replacement in replacements:

        original = replacement["original"]
        translated = replacement["translated"]

        translated_html = translated_html.replace(
            original,
            translated,
            1
        )

    return translated_html
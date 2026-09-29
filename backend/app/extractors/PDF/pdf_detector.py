import fitz


def detect_pdf_type(file_path):
    """
    Detect whether a PDF is mainly native/text-based
    or scanned/image-based.

    Returns:
        "native"
        "scanned"
    """

    document = fitz.open(file_path)

    total_pages = len(document)
    pages_with_text = 0
    total_text_chars = 0

    try:
        for page in document:
            text = page.get_text("text").strip()

            if text:
                pages_with_text += 1
                total_text_chars += len(text)

    finally:
        document.close()

    if total_pages == 0:
        return "scanned"

    text_page_ratio = pages_with_text / total_pages

    # If most pages contain meaningful text,
    # consider it a native PDF.
    if text_page_ratio >= 0.5 and total_text_chars >= 20:
        return "native"

    return "scanned"
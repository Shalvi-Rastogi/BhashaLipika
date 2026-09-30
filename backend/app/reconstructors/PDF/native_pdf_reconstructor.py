import html
import json
import os

import pymupdf as fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")

# lang -> (regular, bold, direction, css font-family)
LANG_CONFIG = {
    "hi": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "ltr", "IndicFont"),
    "mr": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "ltr", "IndicFont"),
    "ur": ("NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Bold.ttf", "rtl", "UrduFont"),
}


def _valid(path):
    return os.path.isfile(path) and os.path.getsize(path) > 10000


def reconstruct_native_pdf(
    original_pdf_path,
    translated_json_path,
    output_pdf_path,
    target_language="hi",
):
    with open(translated_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lang = target_language.lower().strip()
    if lang not in LANG_CONFIG:
        raise ValueError(f"Unsupported PDF language: {lang}")

    regular, bold, direction, family = LANG_CONFIG[lang]
    rtl = direction == "rtl"

    if not _valid(os.path.join(FONT_DIR, regular)):
        raise FileNotFoundError(f"{regular} missing/invalid in assets/fonts")

    archive = fitz.Archive(FONT_DIR)

    css = "@font-face { font-family: %s; src: url(%s); font-weight: normal; }" % (family, regular)
    if _valid(os.path.join(FONT_DIR, bold)):
        css += "@font-face { font-family: %s; src: url(%s); font-weight: bold; }" % (family, bold)
    css += "* { font-family: %s; margin: 0; padding: 0; line-height: 1.4; }" % family

    out = fitz.open()

    try:
        for page_data in data.get("pages", []):
            width = float(page_data.get("width", 595))
            height = float(page_data.get("height", 842))
            page = out.new_page(width=width, height=height)

            text_elements = [
                e for e in page_data.get("elements", []) if e.get("type") == "text"
            ]

            def bottom_limit(el):
                oy1 = el["bbox"][3]
                tops = [
                    e["bbox"][1] for e in text_elements
                    if e is not el and e["bbox"][1] >= oy1 - 1
                ]
                return (min(tops) - 2) if tops else (height - 20)

            for el in text_elements:
                text = el.get("translated_text") or el.get("original_text", "")
                if not isinstance(text, str) or not text.strip():
                    continue

                font = el.get("font") or {}
                x0, y0, x1, y1 = [float(v) for v in el.get("bbox", [0, 0, 100, 20])]
                size = float(font.get("font_size") or 10)

                if rtl:
                    # page ko horizontally mirror karo (bullet right side par)
                    x0, x1 = width - x1, width - x0
                    x0 = min(x0, 72)          # left tak failne do
                    x1 = min(x1, width - 5)
                else:
                    x1 = min(max(x1, width - 72), width - 5)

                y1 = max(bottom_limit(el), y0 + size * 1.5)

                r, g, b = 0, 0, 0
                c = font.get("color")
                if isinstance(c, dict):
                    r, g, b = c.get("r", 0), c.get("g", 0), c.get("b", 0)

                weight = "bold" if font.get("bold") else "normal"
                align = "right" if rtl else "left"

                body = (
                    f'<div dir="{direction}" style="font-size:{size}pt; '
                    f'color:rgb({r},{g},{b}); font-weight:{weight}; '
                    f'text-align:{align};">{html.escape(text)}</div>'
                )

                spare, _ = page.insert_htmlbox(
                    fitz.Rect(x0, y0, x1, y1),
                    body,
                    css=css,
                    archive=archive,
                    scale_low=0,
                )
                if spare < 0:
                    print(f"[PDF] fit nahi hua: {text[:30]!r}")

        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        out.save(output_pdf_path, garbage=4, deflate=True)
    finally:
        out.close()

    return output_pdf_path
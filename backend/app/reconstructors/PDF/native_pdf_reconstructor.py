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


def _fit_font_size(text, font, size, available_width):
    line_width = max(
        font.text_length(line, fontsize=size)
        for line in text.splitlines() or [text]
    )
    if line_width > available_width and line_width:
        return max(1.0, size * available_width / line_width * 0.96)
    return size


def _overlaps_table(element, tables):
    bbox = element.get("bbox")
    if not bbox:
        return False

    text_rect = fitz.Rect(bbox)
    if text_rect.is_empty:
        return False

    for table in tables:
        table_bbox = table.get("bbox")
        if not table_bbox:
            continue

        intersection = text_rect & fitz.Rect(table_bbox)
        if intersection.is_empty:
            continue

        overlap_ratio = (intersection.width * intersection.height) / (
            text_rect.width * text_rect.height
        )
        if overlap_ratio >= 0.5:
            return True

    return False


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
    regular_path = os.path.join(FONT_DIR, regular)
    bold_path = os.path.join(FONT_DIR, bold)

    if not _valid(regular_path):
        raise FileNotFoundError(f"{regular} missing/invalid in assets/fonts")

    archive = fitz.Archive(FONT_DIR)
    font_metrics = {regular: fitz.Font(fontfile=regular_path)}
    if _valid(bold_path):
        font_metrics[bold] = fitz.Font(fontfile=bold_path)

    css = (
        "@font-face { font-family: %s; src: url(%s); "
        "font-weight: normal; font-style: normal; }"
    ) % (family, regular)
    css += (
        "@font-face { font-family: %s; src: url(%s); "
        "font-weight: normal; font-style: italic; }"
    ) % (family, regular)
    if _valid(bold_path):
        css += (
            "@font-face { font-family: %s; src: url(%s); "
            "font-weight: bold; font-style: normal; }"
        ) % (family, bold)
        css += (
            "@font-face { font-family: %s; src: url(%s); "
            "font-weight: bold; font-style: italic; }"
        ) % (family, bold)
    css += "* { font-family: %s; margin: 0; padding: 0; line-height: 1.4; }" % family

    out = fitz.open()

    try:
        for page_data in data.get("pages", []):
            width = float(page_data.get("width", 595))
            height = float(page_data.get("height", 842))
            page = out.new_page(width=width, height=height)

            table_elements = [
                e for e in page_data.get("elements", []) if e.get("type") == "table"
            ]
            text_elements = [
                e
                for e in page_data.get("elements", [])
                if e.get("type") == "text" and not _overlaps_table(e, table_elements)
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
                font_style = "italic" if font.get("italic") else "normal"
                align = "right" if rtl else "left"

                body = (
                    f'<div dir="{direction}" style="font-size:{size}pt; '
                    f'color:rgb({r},{g},{b}); font-weight:{weight}; '
                    f'font-style:{font_style}; '
                    f'text-align:{align}; width:100%; overflow-wrap:anywhere; '
                    f'word-break:break-word;">{html.escape(text)}</div>'
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

            for table in table_elements:
                for row in table.get("rows", []):
                    for cell in row.get("cells", []):
                        cell_bbox = cell.get("bbox")
                        if not cell_bbox:
                            continue

                        x0, y0, x1, y1 = [float(value) for value in cell_bbox]
                        if rtl:
                            x0, x1 = width - x1, width - x0

                        cell_rect = fitz.Rect(x0, y0, x1, y1)
                        page.draw_rect(
                            cell_rect,
                            color=(0.33, 0.33, 0.33),
                            width=0.5,
                            overlay=True,
                        )

                        text = cell.get("translated_text") or cell.get("original_text", "")
                        if not isinstance(text, str) or not text.strip():
                            continue

                        cell_font = cell.get("font") or {}
                        size = float(cell_font.get("font_size") or 9)
                        color = cell_font.get("color") or {}
                        red = color.get("r", 0)
                        green = color.get("g", 0)
                        blue = color.get("b", 0)
                        use_bold = bool(cell_font.get("bold")) and _valid(bold_path)
                        weight = "bold" if use_bold else "normal"
                        font_style = "italic" if cell_font.get("italic") else "normal"
                        align = cell.get("text_alignment") or (
                            "right" if rtl else "left"
                        )
                        if (
                            int(cell.get("rowspan") or 1) > 1
                            and int(cell.get("colspan") or 1) == 1
                        ):
                            align = "right" if rtl else "left"
                        text_rect = fitz.Rect(
                            min(x0, x1) + 2,
                            y0 + 1,
                            max(x0, x1) - 2,
                            y1 - 1,
                        )
                        if text_rect.is_empty or text_rect.is_infinite:
                            continue

                        metrics = font_metrics[bold if use_bold else regular]
                        size = _fit_font_size(
                            text, metrics, size, text_rect.width
                        )

                        body = (
                            f'<div dir="{direction}" style="font-size:{size}pt; '
                            f'color:rgb({red},{green},{blue}); font-weight:{weight}; '
                            f'font-style:{font_style}; '
                            f'text-align:{align}; width:100%; overflow-wrap:anywhere; '
                            f'word-break:break-word;">'
                            f'{html.escape(text).replace(chr(10), "<br>")}</div>'
                        )

                        spare, _ = page.insert_htmlbox(
                            text_rect,
                            body,
                            css=css,
                            archive=archive,
                            scale_low=0,
                        )
                        if spare < 0:
                            print(f"[PDF] Table cell did not fit: {table.get('id')}")

        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        out.save(output_pdf_path, garbage=4, deflate=True)
    finally:
        out.close()

    return output_pdf_path
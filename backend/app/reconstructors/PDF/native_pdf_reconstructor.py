import html
import json
import os

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

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

def _reconstruct_translated_image(image_path, translated_texts, target_language):
    """
    Replace OCR-detected text in an image with translated text.
    """

    try:
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        # Select font
        if target_language in ("hi", "mr"):
            font_path = os.path.join(
                FONT_DIR,
                "NotoSansDevanagari-Regular.ttf"
            )
        else:
            font_path = os.path.join(
                FONT_DIR,
                "NotoSans-Regular.ttf"
            )

        if not os.path.exists(font_path):
            raise FileNotFoundError(
                f"Font not found: {font_path}"
            )

        for item in translated_texts:

            translated = item.get("translated_text", "")
            bbox = item.get("bbox")

            if not translated or not bbox:
                continue

            # OCR bbox is:
            # [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]

            x0 = int(min(point[0] for point in bbox))
            y0 = int(min(point[1] for point in bbox))
            x1 = int(max(point[0] for point in bbox))
            y1 = int(max(point[1] for point in bbox))

            box_width = max(1, x1 - x0)
            box_height = max(1, y1 - y0)

            # Estimate font size from original OCR box
            font_size = max(12, int(box_height * 0.65))

            font = ImageFont.truetype(
                font_path,
                font_size
            )

            # Sample background around the OCR box.
            sample_points = [
                (max(0, x0 - 5), max(0, y0 - 5)),
                (min(image.width - 1, x1 + 5), max(0, y0 - 5)),
                (max(0, x0 - 5), min(image.height - 1, y1 + 5)),
                (min(image.width - 1, x1 + 5), min(image.height - 1, y1 + 5)),
            ]

            background_colors = [
                image.getpixel(point)
                for point in sample_points
            ]

            background = tuple(
                sum(color[channel] for color in background_colors)
                // len(background_colors)
                for channel in range(3)
            )

            # Cover original text
            draw.rectangle(
                [x0, y0, x1, y1],
                fill=background
            )

            # Calculate translated text size
            text_bbox = draw.textbbox(
                (0, 0),
                translated,
                font=font
            )

            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Reduce font size if translation is wider
            while text_width > box_width and font_size > 8:

                font_size -= 1

                font = ImageFont.truetype(
                    font_path,
                    font_size
                )

                text_bbox = draw.textbbox(
                    (0, 0),
                    translated,
                    font=font
                )

                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

            # Center translated text inside original OCR box
            text_x = x0 + (box_width - text_width) / 2
            text_y = y0 + (box_height - text_height) / 2

            draw.text(
                (text_x, text_y),
                translated,
                font=font,
                fill=(0, 0, 0)
            )

        # Save reconstructed image
        translated_image_path = os.path.splitext(
            image_path
        )[0] + "_translated.png"

        image.save(
            translated_image_path
        )

        print(
            f"[PDF] Translated image created: "
            f"{translated_image_path}"
        )

        return translated_image_path

    except Exception as e:

        print(
            f"[PDF] Failed to reconstruct translated image: {e}"
        )

        return image_path

def _span_style(f):
    f = f or {}
    c = f.get("color") or {}
    deco = "underline" if f.get("underline") else "none"
    return (
        f"font-weight:{'bold' if f.get('bold') else 'normal'};"
        f"font-style:{'italic' if f.get('italic') else 'normal'};"
        f"text-decoration:{deco};"
        f"color:rgb({c.get('r', 0)},{c.get('g', 0)},{c.get('b', 0)});"
    )


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
    
    # FIX 1: line-height 1.4 se 1.15 kar diya gaya hai spacing sahi karne ke liye
    css += "* { font-family: %s; margin: 0; padding: 0; line-height: 1.15; }" % family

    out = fitz.open()

    try:
        for page_data in data.get("pages", []):
            width = float(page_data.get("width", 595))
            height = float(page_data.get("height", 842))
            page = out.new_page(width=width, height=height)
            # Reconstruct embedded images
            for image_data in page_data.get("images", []):
                image_path = image_data.get("image_path")
                bbox = image_data.get("bbox")

                if not image_path or not bbox:
                    continue

                image_to_insert = image_path

                translated_texts = image_data.get(
                    "translated_text",
                    []
                )

                if translated_texts:

                    image_to_insert = _reconstruct_translated_image(
                        image_path,
                        translated_texts,
                        target_language
                    )

                try:

                    image_rect = fitz.Rect(
                        float(bbox[0]),
                        float(bbox[1]),
                        float(bbox[2]),
                        float(bbox[3])
                    )

                    page.insert_image(
                        image_rect,
                        filename=image_to_insert
                    )

                    print(
                        f"[PDF] Reconstructed image: "
                        f"page={page_data.get('page_number')}, "
                        f"path={image_to_insert}"
                    )

                except Exception as e:

                    print(
                        f"[PDF] Failed to reconstruct image: {e}"
                    )

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

            # ---------------- TEXT ----------------
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

                # FIX 2: purana y1 limit hata kar, box ko poori height di taaki font chhota na ho
                y1_box = height - 10 

                align = "right" if rtl else "left"
                segs = el.get("segments") or []

                if segs:
                    inner = " ".join(
                        f'<span style="{_span_style(s.get("font"))}">'
                        f'{html.escape(s.get("translated_text") or s.get("text", ""))}</span>'
                        for s in segs
                        if (s.get("translated_text") or s.get("text", "")).strip()
                    )
                else:
                    inner = (
                        f'<span style="{_span_style(font)}">{html.escape(text)}</span>'
                    )

                body = (
                    f'<div dir="{direction}" style="font-size:{size}pt; '
                    f'text-align:{align}; width:100%; overflow-wrap:anywhere; '
                    f'word-break:break-word;">{inner}</div>'
                )

                # FIX 3: y1_box aur scale_low=1.0 ka istemal
                spare, _ = page.insert_htmlbox(
                    fitz.Rect(x0, y0, x1, y1_box),
                    body,
                    css=css,
                    archive=archive,
                    scale_low=1.0, # Font ko chhota hone se rokega
                )
                if spare < 0:
                    print(f"[PDF] fit nahi hua: {text[:30]!r}")

            # ---------------- TABLES (Shalvi, unchanged) ----------------
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
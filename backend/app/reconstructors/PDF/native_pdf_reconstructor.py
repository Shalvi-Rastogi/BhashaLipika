import html
import json
import os

import pymupdf as fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")

# lang -> (regular, bold, direction, css font-family)
LANG_CONFIG = {
    "en": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "ltr", "IndicFont"),
    "hi": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "ltr", "IndicFont"),
    "mr": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "ltr", "IndicFont"),
    "ur": ("NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Bold.ttf", "rtl", "UrduFont"),
}
LANGUAGE_ALIASES = {
    "english": "en",
    "hindi": "hi",
    "marathi": "mr",
    "urdu": "ur",
}


def _normalise_language(language):
    language = language.lower().strip().replace("_", "-").split("-", 1)[0]
    language = LANGUAGE_ALIASES.get(language, language)
    if language not in LANG_CONFIG:
        # NAYA: Crash hone ki jagah default language ("hi") use karega jisme sabse zyada fonts hain
        print(f"Warning: Unsupported PDF language '{language}'. Falling back to default font config.")
        return "hi"
    return language


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

def _item_rect(item, image_width, image_height):
    """Rect (clipped to the image) covered by one translated text entry."""
    bbox = item.get("bbox")
    if not bbox:
        return None
    x0 = max(0, min(float(p[0]) for p in bbox))
    y0 = max(0, min(float(p[1]) for p in bbox))
    x1 = min(image_width, max(float(p[0]) for p in bbox))
    y1 = min(image_height, max(float(p[1]) for p in bbox))
    rect = fitz.Rect(x0, y0, x1, y1)
    return None if rect.is_empty else rect


def _inpaint_text_regions(pixmap, rects):
    """
    Remove the original text by inpainting, so gradient / blurred / photo
    backgrounds stay smooth. Falls back to the original pixmap if OpenCV
    is not available.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[PDF] opencv not installed, skipping inpainting")
        return None

    img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )[:, :, :3].copy()

    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for r in rects:
        pad = 2
        mask[
            max(0, int(r.y0) - pad): min(img.shape[0], int(r.y1) + pad),
            max(0, int(r.x0) - pad): min(img.shape[1], int(r.x1) + pad),
        ] = 255

    cleaned = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    cleaned = np.ascontiguousarray(cleaned)

    return fitz.Pixmap(
        fitz.csRGB, pixmap.width, pixmap.height, cleaned.tobytes(), False
    )

def _estimate_background(pixmap, rect, margin=3):
    """
    Estimate the background colour from pixels just OUTSIDE the rect
    (median per channel), so the text itself does not darken the colour.
    """
    width, height = pixmap.width, pixmap.height
    step = max(1, int(max(rect.width, rect.height) / 20))
    top, bottom = rect.y0 - margin, rect.y1 + margin
    left, right = rect.x0 - margin, rect.x1 + margin

    points = []
    for x in range(int(rect.x0), int(rect.x1) + 1, step):
        points.append((x, top))
        points.append((x, bottom))
    for y in range(int(rect.y0), int(rect.y1) + 1, step):
        points.append((left, y))
        points.append((right, y))

    samples = []
    for x, y in points:
        x = int(min(max(x, 0), width - 1))
        y = int(min(max(y, 0), height - 1))
        samples.append(pixmap.pixel(x, y))

    if not samples:
        return (1, 1, 1)

    color = []
    for channel in range(3):
        values = sorted(s[channel] for s in samples)
        color.append(values[len(values) // 2] / 255)
    return tuple(color)

def _estimate_text_color(pixmap, rect, background, top_fraction=0.05):
    """
    Estimate the original text colour: inside the rect, take the pixels that
    differ the most from the background and average them.
    """
    width, height = pixmap.width, pixmap.height
    x0, y0 = max(0, int(rect.x0)), max(0, int(rect.y0))
    x1, y1 = min(width, int(rect.x1)), min(height, int(rect.y1))
    bg = [c * 255 for c in background]
    step = max(1, int(rect.height / 30))

    samples = []
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            p = pixmap.pixel(x, y)
            dist = sum((p[i] - bg[i]) ** 2 for i in range(3))
            samples.append((dist, p))

    if not samples:
        return (0, 0, 0)

    samples.sort(key=lambda s: s[0], reverse=True)
    count = max(1, int(len(samples) * top_fraction))
    top = samples[:count]
    return tuple(
        int(sum(p[i] for _, p in top) / count) for i in range(3)
    )

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
    Replace OCR text using the same script-aware fonts and shaping as PDF text.
    """

    image_document = None
    try:
        lang = _normalise_language(target_language)
        regular, bold, direction, family = LANG_CONFIG[lang]
        regular_path = os.path.join(FONT_DIR, regular)
        bold_path = os.path.join(FONT_DIR, bold)
        if not _valid(regular_path):
            raise FileNotFoundError(
                f"{regular} missing/invalid in assets/fonts"
            )

        source_image = fitz.Pixmap(image_path)
        if source_image.n not in (3, 4):
            source_image = fitz.Pixmap(fitz.csRGB, source_image)

        image_document = fitz.open()
        page = image_document.new_page(
            width=source_image.width,
            height=source_image.height,
        )
        page.insert_image(page.rect, pixmap=source_image)
        base_pixmap = page.get_pixmap(alpha=False)  # clean copy, used for sampling

        image_width, image_height = page.rect.width, page.rect.height

        # Paint a cleaned copy (original text removed) over the image
        all_rects = [
            r for r in (
                _item_rect(i, image_width, image_height) for i in translated_texts
            ) if r is not None
        ]
        cleaned_pixmap = _inpaint_text_regions(base_pixmap, all_rects)
        if cleaned_pixmap is not None:
            page.insert_image(page.rect, pixmap=cleaned_pixmap)

        archive = fitz.Archive(FONT_DIR)
        css = (
            f"@font-face {{ font-family: {family}; src: url({regular}); "
            "font-weight: normal; }"
        )
        if _valid(bold_path):
            css += (
                f"@font-face {{ font-family: {family}; src: url({bold}); "
                "font-weight: bold; }"
            )
        css += f"* {{ font-family: {family}; margin: 0; padding: 0; line-height: 1.1; }}"

        for item in translated_texts:
            translated = item.get("translated_text", "")
            rect = _item_rect(item, image_width, image_height)
            if not translated or rect is None:
                continue

            background_color = _estimate_background(base_pixmap, rect)

            # Text colour sampled from the ORIGINAL image
            text_r, text_g, text_b = _estimate_text_color(
                base_pixmap, rect, background_color
            )

            # Only needed when inpainting was not possible
            if cleaned_pixmap is None:
                page.draw_rect(rect, color=None, fill=background_color, overlay=True)

            line_height = item.get("line_height")
            font_size = (
                max(8, float(line_height) * 0.7)
                if line_height
                else max(8, rect.height * 0.65)
            )

            body = (
                f'<div dir="{direction}" style="font-size:{font_size}pt; '
                f'color:rgb({text_r},{text_g},{text_b}); '
                f'text-align:center; width:100%; overflow-wrap:anywhere; '
                f'word-break:break-word;">'
                f'{html.escape(translated).replace(chr(10), "<br>")}</div>'
            )
            spare, _ = page.insert_htmlbox(
                rect,
                body,
                css=css,
                archive=archive,
                scale_low=0,
            )
            if spare < 0:
                print(f"[PDF] Translated image text did not fit: {translated[:30]!r}")

        translated_image_path = os.path.splitext(
            image_path
        )[0] + "_translated.png"

        page.get_pixmap(alpha=False).save(translated_image_path)

        print(
            f"[PDF] Translated image created: "
            f"{translated_image_path}"
        )

        return translated_image_path

    except Exception as e:
        print(
            f"[PDF] Failed to reconstruct translated image: {e}"
        )
        raise
    finally:
        if image_document is not None:
            image_document.close()

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

# NAYA: target_language se ="hi" (default value) hata di gayi hai
def reconstruct_native_pdf(
    original_pdf_path,
    translated_json_path,
    output_pdf_path,
    target_language,
):
    with open(translated_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lang = _normalise_language(target_language)

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

                y1_box = max(y1, bottom_limit(el))

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

                spare, _ = page.insert_htmlbox(
                    fitz.Rect(x0, y0, x1, y1_box),
                    body,
                    css=css,
                    archive=archive,
                    scale_low=0.7,
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
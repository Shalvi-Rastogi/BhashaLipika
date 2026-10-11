import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# =========================================================
# PDF IMPORTS
# =========================================================

from app.extractors.PDF.pdf_detector import detect_pdf_type

from app.extractors.PDF.native.native_pdf_extractor import (
    extract_native_pdf_to_json
)
from app.reconstructors.PDF.native_pdf_reconstructor import (
    reconstruct_native_pdf
)


# =========================================================
# LANGUAGE MAPPING
# =========================================================

LANGUAGE_CODES = {
    "en": "eng-latn",
    "english": "eng-latn",
    "hi": "hin-deva",
    "hindi": "hin-deva",
    "mr": "mar-deva",
    "marathi": "mar-deva",
    "ur": "urd-arab",
    "urdu": "urd-arab",
}

# Translation language code -> OCR (easyocr) language code
OCR_LANGUAGE_CODES = {
    "eng-latn": "en",
    "hin-deva": "hi",
    "mar-deva": "mr",
    "urd-arab": "ur",
}


# =========================================================
# BASIC HELPERS
# =========================================================

def _clean_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _normalise_translation(result):
    """Convert the translate_func result (str / dict / list) into a final string."""

    if result is None:
        return ""

    if isinstance(result, str):
        return result.strip()

    if isinstance(result, dict):
        for key in (
            "translated_text", "translation", "translated",
            "text", "output", "result",
        ):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in result.values():
            if isinstance(value, str) and value.strip():
                return value.strip()

    if isinstance(result, list):
        for item in result:
            value = _normalise_translation(item)
            if value:
                return value

    return ""


def _fix_colon(original_text, translated_text, target_language=None):
    """Fix colon rendering issues (visarga replacing ':') after translation."""

    if not isinstance(original_text, str):
        return translated_text

    if not isinstance(translated_text, str):
        return translated_text

    if ":" in original_text and "ः" in translated_text:
        return translated_text.replace("ः", ":")

    return translated_text


# =========================================================
# IMAGE OCR HELPERS
# =========================================================

def _get_image_items(image):
    """
    Return the OCR items of an image that should be translated.

    Preferred: grouped paragraph blocks ("text_blocks"), so a full sentence
    is translated in one go instead of line by line.
    Fallback: raw OCR items ("ocr_data") if grouping produced nothing.
    """

    blocks = image.get("text_blocks")
    if isinstance(blocks, list) and blocks:
        return blocks

    raw = image.get("ocr_data")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    return []


def _to_corner_points(bbox):
    """
    The image reconstructor expects 4 corner points [[x, y], ...].
    Grouped blocks carry a flat [x0, y0, x1, y1] bbox, so convert it.
    Already-point bboxes are returned unchanged.
    """

    if not bbox:
        return None

    if isinstance(bbox[0], (int, float)):
        x0, y0, x1, y1 = bbox[:4]
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    return bbox

_SENTENCE_END = ".।۔!?؟…"


def _match_trailing_punct(original, translated):
    """
    Translators often add a final full stop. If the original text does not
    end with sentence punctuation, strip it from the translation too.
    """

    original = (original or "").rstrip()
    translated = (translated or "").rstrip()

    if original and original[-1] not in _SENTENCE_END:
        while translated and translated[-1] in ".।۔":
            translated = translated[:-1].rstrip()

    return translated

def _split_into_lines(text, weights):
    """
    Split translated text into len(weights) lines. Each line gets a share of
    the words proportional to the length of the matching original line.
    """

    words = text.split()
    n = len(weights)

    if n <= 1 or not words:
        return [text]

    total_weight = float(sum(weights)) or 1.0
    total_chars = sum(len(w) + 1 for w in words)

    lines = [[] for _ in range(n)]
    idx = 0
    cum = 0
    target_end = weights[0] / total_weight * total_chars

    for i, word in enumerate(words):
        remaining_words = len(words) - i
        lines_after = n - idx - 1

        if idx < n - 1 and lines[idx]:
            must_advance = remaining_words <= lines_after
            want_advance = cum + len(word) / 2 > target_end
            if must_advance or want_advance:
                idx += 1
                target_end += weights[idx] / total_weight * total_chars

        lines[idx].append(word)
        cum += len(word) + 1

    # " " keeps an (empty) line truthy so the reconstructor still covers it
    return [" ".join(parts) if parts else " " for parts in lines]


def _build_image_entries(item, translated_text):
    """
    Build reconstructor entries for one OCR block: one entry per original
    line, so the translated text keeps the original line layout.
    All lines of a block share the same line height, so the font size
    stays uniform.
    """

    lines = item.get("lines") or []
    block_bbox = item.get("bbox")

    # Fallback: no line info -> one entry for the whole block
    if not lines or not block_bbox or not isinstance(block_bbox[0], (int, float)):
        bbox = _to_corner_points(block_bbox)
        if not bbox:
            return []
        entry = {"bbox": bbox, "translated_text": translated_text}
        if item.get("line_height"):
            entry["line_height"] = item["line_height"]
        return [entry]

    bx0, _, bx1, _ = block_bbox[:4]

    # One common line height for the whole block (average of its lines)
    heights = [l["bbox"][3] - l["bbox"][1] for l in lines]
    avg_h = sum(heights) / len(heights)

    weights = [max(1, len(l.get("text", ""))) for l in lines]
    parts = _split_into_lines(translated_text, weights)

    entries = []
    for line, part, h in zip(lines, parts, heights):
        x0, y0, x1, y1 = line["bbox"]
        cy = (y0 + y1) / 2

        # Rect is at least avg_h tall (so the text is never squeezed) and
        # still covers the full original line (descenders included)
        half = max(h, avg_h) / 2 + avg_h * 0.15

        entries.append({
            "bbox": [
                [bx0 - avg_h * 0.3, cy - half], [bx1 + avg_h * 0.3, cy - half],
                [bx1 + avg_h * 0.3, cy + half], [bx0 - avg_h * 0.3, cy + half],
            ],
            "translated_text": part,
            "line_height": avg_h,
        })

    return entries

# =========================================================
# COLLECT TEXT
# =========================================================

def _collect_translatable_texts(document_data):
    """
    Collect every text that needs translation from the PDF JSON:
      1. normal text elements
      2. text segments
      3. table cell text
      4. image OCR text (grouped blocks)

    A set is used so duplicate texts are translated only once.
    """

    texts = set()

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    for segment in segments:
                        text = _clean_text(segment.get("text", ""))
                        if text:
                            texts.add(text)
                else:
                    text = _clean_text(element.get("original_text", ""))
                    if text:
                        texts.add(text)

            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        text = _clean_text(cell.get("original_text", ""))
                        if text:
                            texts.add(text)

        # Image OCR text
        for image in page.get("images", []):
            for item in _get_image_items(image):
                text = _clean_text(item.get("text", ""))
                if text:
                    texts.add(text)

    return texts


# =========================================================
# TRANSLATION
# =========================================================

def _translate_text(
    text,
    translate_func,
    source_language,
    target_language,
):
    """Translate one text through translate_func. Raises on failure."""

    text = _clean_text(text)

    if not text:
        return ""

    # Nothing to do when source and target are the same
    if source_language == target_language:
        return text

    try:
        result = translate_func(
            text,
            source_language,
            target_language
        )

        translated = _normalise_translation(result)

        if translated:
            return translated

        raise RuntimeError(
            f"PDF translator returned an empty result for "
            f"{ascii(text[:80])}."
        )

    except Exception as error:
        print(
            f"[PDF][ERROR] Translation failed for "
            f"{ascii(text[:80])}: {error}"
        )

        raise RuntimeError(
            f"PDF translation failed for {ascii(text[:80])}."
        ) from error


def _translate_unique_texts(texts, translate_func, source_language, target_language):
    """Translate all unique texts in parallel and return {original: translated}."""

    translation_cache = {}

    if not texts:
        return translation_cache

    print(f"[PDF] Total unique texts to translate: {len(texts)}")

    failures = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_text = {
            executor.submit(
                _translate_text,
                text,
                translate_func,
                source_language,
                target_language,
            ): text
            for text in texts
        }

        for future in as_completed(future_to_text):
            original_text = future_to_text[future]

            try:
                translated_text = future.result()
            except Exception as error:
                print(
                    f"[PDF][ERROR] Future failed for "
                    f"{original_text[:80]!r}: {error}"
                )
                failures.append((original_text, error))
                continue

            if not translated_text:
                failures.append(
                    (
                        original_text,
                        RuntimeError("Translator returned an empty result.")
                    )
                )
                continue

            translation_cache[original_text] = translated_text

            print(
                f"[PDF] TRANSLATED: "
                f"{ascii(original_text[:50])} -> "
                f"{ascii(translation_cache[original_text][:50])}"
            )

    if failures:
        failed_text, error = failures[0]
        raise RuntimeError(
            f"PDF translation failed for {len(failures)} text item(s); "
            f"first failed item: {ascii(failed_text[:80])}."
        ) from error

    return translation_cache


# =========================================================
# APPLY TRANSLATIONS TO JSON
# =========================================================

def _apply_translations(
    document_data,
    translation_cache,
    target_language
):
    """
    Write the translations from the cache back into the JSON structure.

    - text elements and their segments
    - table cells
    - image OCR blocks (image["translated_text"] is the list the
      reconstructor reads: [{"bbox": 4 corner points, "translated_text": ...}])
    """

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            # ---------------- TEXT ----------------
            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    translated_segments = []

                    for segment in segments:
                        original_segment = _clean_text(segment.get("text", ""))

                        if not original_segment:
                            segment["translated_text"] = ""
                            continue

                        translated_segment = translation_cache.get(
                            original_segment, original_segment
                        )
                        translated_segment = _fix_colon(
                            original_segment, translated_segment, target_language
                        )

                        segment["translated_text"] = translated_segment
                        translated_segments.append(translated_segment)

                    element["translated_text"] = " ".join(
                        x.strip() for x in translated_segments if x and x.strip()
                    )

                else:
                    original_text = _clean_text(element.get("original_text", ""))
                    translated_text = translation_cache.get(
                        original_text, original_text
                    )
                    element["translated_text"] = _fix_colon(
                        original_text, translated_text, target_language
                    )

            # ---------------- TABLE ----------------
            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        original_text = _clean_text(cell.get("original_text", ""))

                        if not original_text:
                            cell["translated_text"] = ""
                            continue

                        translated = translation_cache.get(
                            original_text, original_text
                        )
                        cell["translated_text"] = _fix_colon(
                            original_text, translated, target_language
                        )

        # ---------------- IMAGES ----------------
                
        for image in page.get("images", []):
            translated_items = []

            for item in _get_image_items(image):
                original_text = _clean_text(item.get("text", ""))

                if not original_text:
                    item["translated_text"] = ""
                    continue

                translated_text = translation_cache.get(
                    original_text, original_text
                )
                translated_text = _fix_colon(
                    original_text, translated_text, target_language
                )

                translated_text = _match_trailing_punct(
                    original_text, translated_text
                )

                item["translated_text"] = translated_text
                translated_items.extend(
                    _build_image_entries(item, translated_text)
                )

            image["translated_text"] = translated_items

    return document_data


# =========================================================
# COVERAGE CHECK
# =========================================================

def _count_coverage(document_data):
    """Count how many translatable items got a non-empty translation."""

    translated_count = 0
    total_count = 0

    for page in document_data.get("pages", []):
        for element in page.get("elements", []):
            element_type = element.get("type")

            if element_type == "text":
                segments = element.get("segments") or []

                if segments:
                    for segment in segments:
                        if segment.get("text", "").strip():
                            total_count += 1
                            if segment.get("translated_text", "").strip():
                                translated_count += 1

                elif element.get("original_text", "").strip():
                    total_count += 1
                    if element.get("translated_text", "").strip():
                        translated_count += 1

            elif element_type == "table":
                for row in element.get("rows", []):
                    for cell in row.get("cells", []):
                        if cell.get("original_text", "").strip():
                            total_count += 1
                            if cell.get("translated_text", "").strip():
                                translated_count += 1

        for image in page.get("images", []):
            for item in _get_image_items(image):
                text = item.get("text", "")
                if isinstance(text, str) and text.strip():
                    total_count += 1

                    translated = item.get("translated_text", "")
                    if isinstance(translated, str) and translated.strip():
                        translated_count += 1

    return translated_count, total_count


# =========================================================
# MAIN PIPELINE
# =========================================================

def process_pdf_pipeline(
    file_path,
    filename,
    target_language="hi",
    tgt_lang_code=None,
    output_folder=None,
    translate_func=None,
    source_language="eng-latn",
    source_language_name=None,
):
    """
    Complete native PDF pipeline:

    1. Original PDF
    2. Extract original JSON (text, tables, images + OCR)
    3. Translate
    4. Save translated JSON
    5. Reconstruct translated PDF
    """

    # ---------- PDF type check ----------
    pdf_type = detect_pdf_type(file_path)
    print(f"[PDF] Detected type: {pdf_type}")

    if pdf_type != "native":
        # Scanned PDF pipeline is not implemented yet, continue anyway
        print("[PDF] Continuing with image extraction test...")

    if translate_func is None:
        raise ValueError("translate_func is required for PDF translation.")

    # ---------- Output directory ----------
    if output_folder is None:
        output_folder = os.path.dirname(file_path)
    os.makedirs(output_folder, exist_ok=True)

    # ---------- Language ----------
    language_key = (target_language or "hi").lower().strip()

    if tgt_lang_code is None:
        tgt_lang_code = LANGUAGE_CODES.get(language_key)

    if not tgt_lang_code:
        raise ValueError(f"Unsupported target language: {target_language}")

    print("=" * 70)
    print("[PDF] Starting PDF pipeline")
    print(f"[PDF] Input       : {file_path}")
    print(f"[PDF] Source code : {source_language}")
    print(f"[PDF] Target      : {language_key}")
    print(f"[PDF] Target code : {tgt_lang_code}")
    print("=" * 70)

    # ---------- File names ----------
    base_name = os.path.splitext(os.path.basename(filename))[0]

    source_language_key = (
        source_language_name
        or source_language.split("-")[0]
    )

    original_json_path = os.path.join(
        output_folder, f"{base_name}_original.json"
    )
    translated_json_path = os.path.join(
        output_folder,
        f"{base_name}_translated_{source_language_key}_to_{language_key}.json"
    )
    reconstructed_pdf_path = os.path.join(
        output_folder,
        f"{base_name}_reconstructed_{source_language_key}_to_{language_key}.pdf"
    )

    # ---------- OCR languages (based on SOURCE language) ----------
    ocr_language = OCR_LANGUAGE_CODES.get(source_language, "en")
    ocr_languages = [ocr_language]
    if ocr_language != "en":
        ocr_languages.append("en")

    # ---------- Step 1: Extract ----------
    print("[PDF] Step 1: Extracting native PDF...")
    document_data = extract_native_pdf_to_json(
        file_path,
        original_json_path,
        ocr_languages=ocr_languages,
    )
    print(f"[PDF] Original JSON created: {original_json_path}")

    # ---------- Step 2: Collect ----------
    print("[PDF] Step 2: Collecting text...")
    texts = _collect_translatable_texts(document_data)
    print(f"[PDF] Text items found: {len(texts)}")

    # ---------- Step 3: Translate ----------
    print("[PDF] Step 3: Translating text...")
    translation_cache = _translate_unique_texts(
        texts=texts,
        translate_func=translate_func,
        source_language=source_language,
        target_language=tgt_lang_code,
    )

    if not translation_cache and texts:
        raise RuntimeError(
            "PDF translation failed: no translations were returned by translate_func."
        )

    # ---------- Step 4: Apply ----------
    print("[PDF] Step 4: Applying translations to JSON...")
    document_data = _apply_translations(
        document_data, translation_cache, language_key
    )

    translated_count, total_count = _count_coverage(document_data)
    print(f"[PDF] Translation coverage: {translated_count}/{total_count}")

    # ---------- Step 5: Save translated JSON ----------
    print("[PDF] Step 5: Saving translated JSON...")
    with open(translated_json_path, "w", encoding="utf-8") as json_file:
        json.dump(document_data, json_file, indent=4, ensure_ascii=False)
    print(f"[PDF] Translated JSON created: {translated_json_path}")

    # ---------- Step 6: Reconstruct ----------
    print("[PDF] Step 6: Reconstructing translated PDF...")
    reconstruct_native_pdf(
        original_pdf_path=file_path,
        translated_json_path=translated_json_path,
        output_pdf_path=reconstructed_pdf_path,
        target_language=language_key,
    )
    print(f"[PDF] Reconstructed PDF created: {reconstructed_pdf_path}")

    print("=" * 70)
    print("[PDF] PIPELINE COMPLETED")
    print("=" * 70)

    return {
        # Keys used by the router / frontend
        "json_file": os.path.basename(original_json_path),
        "translated_json_file": os.path.basename(translated_json_path),
        "reconstructed_pdf_file": os.path.basename(reconstructed_pdf_path),
        "reconstructed_file": os.path.basename(reconstructed_pdf_path),
        "output_filename": os.path.basename(reconstructed_pdf_path),

        # Extra info
        "status": "success",
        "document_name": filename,
        "pdf_type": pdf_type,
        "target_language": language_key,
        "original_json": original_json_path,
        "translated_json": translated_json_path,
        "reconstructed_pdf": reconstructed_pdf_path,
        "translation_count": translated_count,
        "total_translatable_items": total_count,
        "data": document_data,
    }
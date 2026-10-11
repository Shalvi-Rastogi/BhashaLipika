import os
import pymupdf as fitz

from app.extractors.PPTX.image_extractor import extract_text_from_image
from app.extractors.PDF.native.ocr_grouping import group_ocr_results


def _normalise_ocr(ocr_data):
    
    if isinstance(ocr_data, dict):
        for key in ("items", "results", "blocks", "lines", "text_items", "data"):
            if isinstance(ocr_data.get(key), list):
                ocr_data = ocr_data[key]
                break
        else:
            return []

    if not isinstance(ocr_data, list):
        return []

    results = []
    for item in ocr_data:
        try:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                bbox, text = item[0], item[1]
                conf = item[2] if len(item) > 2 else 1.0
            elif isinstance(item, dict):
                bbox = item.get("bbox") or item.get("box")
                text = item.get("text") or item.get("original_text") or ""
                conf = item.get("confidence", item.get("conf", 1.0))
            else:
                continue

            if bbox is None or not str(text).strip():
                continue

            results.append((bbox, str(text), float(conf)))
        except Exception:
            continue

    return results


def extract_native_pdf_images(
    document,
    output_directory,
    ocr_languages=None,
):
    

    os.makedirs(output_directory, exist_ok=True)

    images_data = []

    for page_index, page in enumerate(document):

        page_number = page_index + 1
        image_infos = page.get_image_info(xrefs=True)

        for image_index, image_info in enumerate(image_infos, start=1):

            xref = image_info.get("xref")

            if not xref:
                continue

            try:
                image_data = document.extract_image(xref)

                image_bytes = image_data["image"]
                extension = image_data.get("ext", "png")

                image_filename = f"page_{page_number}_image_{image_index}.{extension}"
                image_path = os.path.join(output_directory, image_filename)

                with open(image_path, "wb") as image_file:
                    image_file.write(image_bytes)

                bbox = image_info.get("bbox")

                print(f"[PDF] Extracted image: page={page_number}, image={image_index}")

                # ---- OCR ----
                ocr_data = extract_text_from_image(
                    image_path,
                    languages=ocr_languages
                )
                print(f"[PDF] OCR RESULT: {ascii(ocr_data)}")

                # ---- GROUPING (tukde -> paragraph blocks) ----
                raw_results = _normalise_ocr(ocr_data)
                text_blocks = group_ocr_results(raw_results)

                if raw_results and not text_blocks:
                    print("[PDF] Warning: OCR mila par grouping empty aayi (sab noise filter ho gaya?)")
                if not raw_results and ocr_data:
                    print(f"[PDF] Warning: OCR format samajh nahi aaya, type={type(ocr_data)}")

                for block_index, block in enumerate(text_blocks, start=1):
                    block["id"] = f"p{page_number}_i{image_index}_b{block_index}"
                    block["translated_text"] = ""

                print(f"[PDF] OCR blocks after grouping: {len(text_blocks)}")

                images_data.append({
                    "page_number": page_number,
                    "image_index": image_index,
                    "xref": xref,
                    "image_path": image_path,
                    "bbox": [round(v, 2) for v in bbox] if bbox else None,
                    "ocr_data": ocr_data,          # raw, as it is
                    "text_blocks": text_blocks,    # NAYA: grouped paragraphs
                    "translated_text": []
                })

            except Exception as e:
                print(f"[PDF] Failed to extract image on page {page_number}: {e}")

    return images_data
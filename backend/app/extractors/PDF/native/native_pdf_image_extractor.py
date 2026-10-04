import os
import pymupdf as fitz

from app.extractors.PPTX.image_extractor import extract_text_from_image

def extract_native_pdf_images(
    document,
    output_directory,
    ocr_languages=None,
):
    """
    Extract embedded images from a native PDF.

    Returns image information including:
    - page number
    - image path
    - image bounding box
    - image xref
    """

    os.makedirs(output_directory, exist_ok=True)

    images_data = []

    for page_index, page in enumerate(document):

        page_number = page_index + 1

        # Get image information including their positions
        image_infos = page.get_image_info(xrefs=True)

        for image_index, image_info in enumerate(image_infos, start=1):

            xref = image_info.get("xref")

            if not xref:
                continue

            try:
                image_data = document.extract_image(xref)

                image_bytes = image_data["image"]
                extension = image_data.get("ext", "png")

                image_filename = (
                    f"page_{page_number}_image_{image_index}.{extension}"
                )

                image_path = os.path.join(
                    output_directory,
                    image_filename
                )

                with open(image_path, "wb") as image_file:
                    image_file.write(image_bytes)

                bbox = image_info.get("bbox")

                print(f"[PDF] Extracted image: page={page_number}, image={image_index}")

                # Run OCR on the extracted image
                ocr_data = extract_text_from_image(
                    image_path,
                    languages=ocr_languages
                )

                print(f"[PDF] OCR RESULT: {ascii(ocr_data)}")

                images_data.append({
                    "page_number": page_number,
                    "image_index": image_index,
                    "xref": xref,
                    "image_path": image_path,
                    "bbox": [
                        round(value, 2)
                        for value in bbox
                    ] if bbox else None,
                    "ocr_data": ocr_data,
                    "translated_text": []
                })

                print(
                    f"[PDF] Extracted image: "
                    f"page={page_number}, "
                    f"image={image_index}"
                )

            except Exception as e:
                print(
                    f"[PDF] Failed to extract image "
                    f"on page {page_number}: {e}"
                )

    return images_data
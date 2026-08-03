import os
import zipfile

from app.extractors.ocr_extractor import extract_text_from_image


def extract_images_from_docx(docx_path, output_folder="app/temp"):
    """
    Extract all images from a DOCX file, save them temporarily,
    perform OCR on each image, and return the extracted text.
    """

    # Create temp folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    extracted_images = []

    # DOCX is actually a ZIP file
    with zipfile.ZipFile(docx_path, "r") as docx:

        # Find all image files inside word/media/
        image_files = [
            f for f in docx.namelist()
            if f.startswith("word/media/")
        ]

        for index, image_file in enumerate(image_files, start=1):

            # Get extension (.png, .jpg, etc.)
            extension = os.path.splitext(image_file)[1]

            # Save image
            output_path = os.path.join(
                output_folder,
                f"image_{index}{extension}"
            )

            with open(output_path, "wb") as img:
                img.write(docx.read(image_file))

            # Perform OCR
            ocr_result = extract_text_from_image(output_path)

            extracted_images.append({
                "image_name": os.path.basename(output_path),
                "image_path": output_path,
                "ocr": ocr_result
            })

    return extracted_images
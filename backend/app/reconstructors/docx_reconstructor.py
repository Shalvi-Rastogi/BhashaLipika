from docx import Document
import json
import os
import zipfile
import shutil
import tempfile

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# FONT
# ============================================================

def get_font_path():
    """
    Find a Unicode font available on Windows.

    Nirmala UI supports Hindi/Devanagari.
    """

    possible_fonts = [
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\NirmalaUI.ttf",
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path

    return None


# ============================================================
# FONT SIZE CALCULATION
# ============================================================

def calculate_font_size(
    draw,
    text,
    box_width,
    box_height,
    font_path
):
    """
    Calculate a font size based on the original
    OCR bounding-box dimensions.

    The translated text is also reduced if it
    does not fit inside the original text area.
    """

    # Initial estimate based on original text height
    font_size = max(
        8,
        int(box_height * 0.75)
    )

    # If font is unavailable
    if font_path is None:
        return None

    while font_size >= 8:

        try:
            font = ImageFont.truetype(
                font_path,
                font_size
            )

            bbox = draw.textbbox(
                (0, 0),
                text,
                font=font
            )

            text_width = (
                bbox[2] - bbox[0]
            )

            text_height = (
                bbox[3] - bbox[1]
            )

            # Text should fit inside original box
            if (
                text_width <= box_width
                and
                text_height <= box_height
            ):
                return font

            font_size -= 1

        except Exception:
            break

    # Minimum fallback size
    try:
        return ImageFont.truetype(
            font_path,
            8
        )
    except Exception:
        return ImageFont.load_default()


# ============================================================
# BACKGROUND COLOR
# ============================================================

def get_background_color(
    image,
    x1,
    y1,
    x2,
    y2
):
    """
    Estimate the background color around the OCR text.

    This is better than always using white.
    """

    try:

        pixels = []

        # Pixels just outside the text bounding box
        sample_points = [
            (max(0, x1 - 2), max(0, y1)),
            (max(0, x1 - 2), min(image.height - 1, y2)),
            (min(image.width - 1, x2 + 2), max(0, y1)),
            (
                min(image.width - 1, x2 + 2),
                min(image.height - 1, y2)
            ),
        ]

        for point in sample_points:
            pixels.append(
                image.getpixel(point)
            )

        if pixels:
            r = sum(
                pixel[0]
                for pixel in pixels
            ) // len(pixels)

            g = sum(
                pixel[1]
                for pixel in pixels
            ) // len(pixels)

            b = sum(
                pixel[2]
                for pixel in pixels
            ) // len(pixels)

            return (r, g, b)

    except Exception:
        pass

    return "white"


# ============================================================
# IMAGE RECONSTRUCTION
# ============================================================

def reconstruct_image(
    original_image_path,
    image_element,
    output_image_path
):
    """
    Reconstruct an image by replacing OCR-detected
    text with translated text.

    Font size is calculated from the OCR bounding box.
    """

    try:

        # ----------------------------------------------------
        # Load image
        # ----------------------------------------------------

        image = Image.open(
            original_image_path
        ).convert("RGB")

        draw = ImageDraw.Draw(image)

        # ----------------------------------------------------
        # Get OCR details
        # ----------------------------------------------------

        ocr_details = image_element.get(
            "ocr_details",
            []
        )

        if not ocr_details:

            print(
                "No OCR details found."
            )

            image.save(
                output_image_path
            )

            return True

        # ----------------------------------------------------
        # Font
        # ----------------------------------------------------

        font_path = get_font_path()

        if font_path:

            print(
                f"Using font: {font_path}"
            )

        else:

            print(
                "Unicode font not found. "
                "Using default PIL font."
            )

        # ----------------------------------------------------
        # Process every OCR text
        # ----------------------------------------------------

        for item in ocr_details:

            original_text = item.get(
                "text",
                ""
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Translation may be stored as:
            #
            # item["translated_text"]
            #
            # OR fallback to item["text"]
            # ------------------------------------------------

            translated_text = item.get(
                "translated_text",
                ""
            )

            if not translated_text:

                translated_text = item.get(
                    "text",
                    ""
                )

            bbox = item.get(
                "bbox"
            )

            # ------------------------------------------------
            # Validation
            # ------------------------------------------------

            if not bbox:

                print(
                    f"No bounding box for: "
                    f"{original_text}"
                )

                continue

            if not translated_text:

                print(
                    f"No translated text for: "
                    f"{original_text}"
                )

                continue

            # ------------------------------------------------
            # Convert bbox to rectangle
            # ------------------------------------------------

            x1 = min(
                int(point[0])
                for point in bbox
            )

            y1 = min(
                int(point[1])
                for point in bbox
            )

            x2 = max(
                int(point[0])
                for point in bbox
            )

            y2 = max(
                int(point[1])
                for point in bbox
            )

            box_width = max(
                1,
                x2 - x1
            )

            box_height = max(
                1,
                y2 - y1
            )

            print(
                f"\nOriginal text: "
                f"{original_text}"
            )

            print(
                f"Translated text: "
                f"{translated_text}"
            )

            print(
                f"BBox: "
                f"{x1}, {y1}, {x2}, {y2}"
            )

            print(
                f"Original text area: "
                f"{box_width} x {box_height}"
            )

            # ------------------------------------------------
            # Estimate background
            # ------------------------------------------------

            background_color = (
                get_background_color(
                    image,
                    x1,
                    y1,
                    x2,
                    y2
                )
            )

            # ------------------------------------------------
            # Remove original text
            # ------------------------------------------------

            draw.rectangle(
                [
                    x1,
                    y1,
                    x2,
                    y2
                ],
                fill=background_color
            )

            # ------------------------------------------------
            # Calculate font
            # ------------------------------------------------

            font = calculate_font_size(
                draw,
                translated_text,
                box_width,
                box_height,
                font_path
            )

            if font is None:

                font = ImageFont.load_default()

            # ------------------------------------------------
            # Get translated text dimensions
            # ------------------------------------------------

            text_bbox = draw.textbbox(
                (0, 0),
                translated_text,
                font=font
            )

            text_width = (
                text_bbox[2]
                - text_bbox[0]
            )

            text_height = (
                text_bbox[3]
                - text_bbox[1]
            )

            # ------------------------------------------------
            # Center text inside original text area
            # ------------------------------------------------

            text_x = (
                x1
                + (box_width - text_width) / 2
            )

            text_y = (
                y1
                + (box_height - text_height) / 2
                - text_bbox[1]
            )

            # ------------------------------------------------
            # Draw translated text
            # ------------------------------------------------

            draw.text(
                (
                    text_x,
                    text_y
                ),
                translated_text,
                fill="black",
                font=font
            )

            print(
                "Image text reconstructed successfully."
            )

        # ----------------------------------------------------
        # Save reconstructed image
        # ----------------------------------------------------

        image.save(
            output_image_path
        )

        print(
            f"Reconstructed image saved: "
            f"{output_image_path}"
        )

        return True

    except Exception as e:

        print(
            f"Image reconstruction failed: {e}"
        )

        return False


# ============================================================
# EXTRACT IMAGES FROM DOCX
# ============================================================

def extract_images_from_docx(
    docx_path,
    temp_folder
):
    """
    Extract all images directly from the input DOCX.

    No manually created temp images are required.
    """

    extracted_images = []

    os.makedirs(
        temp_folder,
        exist_ok=True
    )

    try:

        with zipfile.ZipFile(
            docx_path,
            "r"
        ) as z:

            for file_name in z.namelist():

                if not file_name.startswith(
                    "word/media/"
                ):
                    continue

                image_name = os.path.basename(
                    file_name
                )

                output_path = os.path.join(
                    temp_folder,
                    image_name
                )

                with open(
                    output_path,
                    "wb"
                ) as f:

                    f.write(
                        z.read(file_name)
                    )

                extracted_images.append(
                    {
                        "name": image_name,
                        "path": output_path,
                        "zip_name": file_name
                    }
                )

                print(
                    f"Extracted image: "
                    f"{image_name}"
                )

        print(
            f"Total images extracted: "
            f"{len(extracted_images)}"
        )

        return extracted_images

    except Exception as e:

        print(
            f"Image extraction failed: {e}"
        )

        return []


# ============================================================
# REPLACE IMAGES INSIDE DOCX
# ============================================================

def replace_images_in_docx(
    original_docx_path,
    output_docx_path,
    reconstructed_images
):
    """
    Replace images inside DOCX ZIP package.

    Mapping is done using image filename instead of
    assuming that list order is always the same.
    """

    try:

        reconstructed_map = {}

        for item in reconstructed_images:

            reconstructed_map[
                item["original_name"]
            ] = item["reconstructed_path"]

        # ----------------------------------------------------
        # Temporary DOCX
        # ----------------------------------------------------

        temp_docx = (
            output_docx_path
            + ".tmp"
        )

        with zipfile.ZipFile(
            original_docx_path,
            "r"
        ) as zin:

            with zipfile.ZipFile(
                temp_docx,
                "w",
                zipfile.ZIP_DEFLATED
            ) as zout:

                for item in zin.infolist():

                    data = zin.read(
                        item.filename
                    )

                    # ------------------------------------------------
                    # Check image
                    # ------------------------------------------------

                    if item.filename.startswith(
                        "word/media/"
                    ):

                        image_name = os.path.basename(
                            item.filename
                        )

                        print(
                            f"Checking DOCX image: "
                            f"{image_name}"
                        )

                        reconstructed_path = (
                            reconstructed_map.get(
                                image_name
                            )
                        )

                        if (
                            reconstructed_path
                            and
                            os.path.exists(
                                reconstructed_path
                            )
                        ):

                            with open(
                                reconstructed_path,
                                "rb"
                            ) as image_file:

                                data = (
                                    image_file.read()
                                )

                            print(
                                f"Replacing: "
                                f"{item.filename}"
                            )

                    zout.writestr(
                        item,
                        data
                    )

        # ----------------------------------------------------
        # Replace final DOCX
        # ----------------------------------------------------

        os.replace(
            temp_docx,
            output_docx_path
        )

        print(
            "All reconstructed images "
            "replaced inside DOCX."
        )

        return True

    except Exception as e:

        print(
            f"Failed to replace images "
            f"in DOCX: {e}"
        )

        return False


# ============================================================
# PARAGRAPH RECONSTRUCTION
# ============================================================

def reconstruct_paragraphs(
    document,
    elements
):

    print(
        "\n========== PARAGRAPH RECONSTRUCTION =========="
    )

    text_elements = [
        element
        for element in elements
        if element.get("type") in [
            "paragraph",
            "heading",
            "list_item"
        ]
    ]

    paragraphs = document.paragraphs

    print(
        "Original paragraphs:",
        len(paragraphs)
    )

    print(
        "Translated text elements:",
        len(text_elements)
    )

    original_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if paragraph.text.strip()
    ]

    for paragraph, element in zip(
        original_paragraphs,
        text_elements
    ):

        translated_text = element.get(
            "text",
            ""
        )

        if not translated_text:
            continue

        if paragraph.runs:

            paragraph.runs[0].text = (
                translated_text
            )

            for run in paragraph.runs[1:]:

                run.text = ""

        else:

            paragraph.add_run(
                translated_text
            )


# ============================================================
# TABLE RECONSTRUCTION
# ============================================================

def reconstruct_tables(
    document,
    elements
):

    print(
        "\n========== TABLE RECONSTRUCTION =========="
    )

    table_elements = [
        element
        for element in elements
        if element.get("type") == "table"
    ]

    print(
        "Original tables:",
        len(document.tables)
    )

    print(
        "Translated tables:",
        len(table_elements)
    )

    for table_index, table in enumerate(
        document.tables
    ):

        translated_table = None

        for element in table_elements:

            if (
                element.get("table_index")
                == table_index
            ):

                translated_table = element
                break

        if translated_table is None:

            continue

        translated_cells = [
            cell
            for row in translated_table.get(
                "rows",
                []
            )
            for cell in row.get(
                "cells",
                []
            )
        ]

        for row_index, row in enumerate(
            table.rows
        ):

            for column_index, cell in enumerate(
                row.cells
            ):

                translated_text = None

                for translated_cell in (
                    translated_cells
                ):

                    if (
                        translated_cell.get(
                            "row"
                        )
                        == row_index
                        and
                        translated_cell.get(
                            "column"
                        )
                        == column_index
                    ):

                        translated_text = (
                            translated_cell.get(
                                "text",
                                ""
                            )
                        )

                        break

                if translated_text is None:

                    continue

                if cell.paragraphs:

                    target_paragraph_index = next(
                        (
                            index
                            for index, paragraph
                            in enumerate(
                                cell.paragraphs
                            )
                            if paragraph.text.strip()
                        ),
                        0
                    )

                    paragraph = (
                        cell.paragraphs[
                            target_paragraph_index
                        ]
                    )

                    if paragraph.runs:

                        paragraph.runs[0].text = (
                            translated_text
                        )

                        for run in (
                            paragraph.runs[1:]
                        ):

                            run.text = ""

                    else:

                        paragraph.add_run(
                            translated_text
                        )

                    for index, other_paragraph in (
                        enumerate(
                            cell.paragraphs
                        )
                    ):

                        if (
                            index
                            == target_paragraph_index
                        ):
                            continue

                        for run in (
                            other_paragraph.runs
                        ):

                            run.text = ""

                else:

                    cell.text = (
                        translated_text
                    )


# ============================================================
# IMAGE RECONSTRUCTION
# ============================================================

def reconstruct_images(
    original_docx_path,
    elements,
    temp_folder
):

    print(
        "\n========== IMAGE RECONSTRUCTION =========="
    )

    image_elements = [
        element
        for element in elements
        if element.get("type") == "image_text"
    ]

    print(
        "Translated image elements:",
        len(image_elements)
    )

    if not image_elements:

        print(
            "No image_text elements found."
        )

        return []

    # --------------------------------------------------------
    # Extract actual images from DOCX
    # --------------------------------------------------------

    extracted_images = (
        extract_images_from_docx(
            original_docx_path,
            temp_folder
        )
    )

    if not extracted_images:

        print(
            "No images found inside DOCX."
        )

        return []

    reconstructed_images = []

    # --------------------------------------------------------
    # Match image element with extracted image
    # --------------------------------------------------------

    for index, image_element in enumerate(
        image_elements
    ):

        image_name = image_element.get(
            "image_name",
            ""
        )

        print(
            f"\nProcessing image element "
            f"{index + 1}: {image_name}"
        )

        # ----------------------------------------------------
        # Find matching image
        #
        # Handles:
        # image_1.png
        # image1.png
        # ----------------------------------------------------

        matching_image = None

        for extracted in extracted_images:

            extracted_name = extracted["name"]

            if (
                extracted_name == image_name
                or
                extracted_name.replace(
                    "image",
                    "image_"
                )
                == image_name
            ):

                matching_image = extracted
                break

        # ----------------------------------------------------
        # If exact name is not found, use order
        # ----------------------------------------------------

        if matching_image is None:

            if index < len(extracted_images):

                matching_image = (
                    extracted_images[index]
                )

        if matching_image is None:

            print(
                f"Could not match image: "
                f"{image_name}"
            )

            continue

        original_image_path = (
            matching_image["path"]
        )

        reconstructed_image_path = os.path.join(
            temp_folder,
            f"reconstructed_"
            f"{index + 1}_"
            f"{matching_image['name']}"
        )

        print(
            f"Using original image: "
            f"{original_image_path}"
        )

        success = reconstruct_image(
            original_image_path,
            image_element,
            reconstructed_image_path
        )

        if success:

            reconstructed_images.append(
                {
                    "original_name":
                        matching_image["name"],

                    "reconstructed_path":
                        reconstructed_image_path
                }
            )

    print(
        f"\nReconstructed images: "
        f"{len(reconstructed_images)}"
    )

    return reconstructed_images


# ============================================================
# MAIN DOCX RECONSTRUCTION
# ============================================================

def reconstruct_docx(
    original_docx_path,
    translated_json_path,
    output_docx_path
):
    """
    Complete DOCX reconstruction.

    Handles:

    1. Paragraphs
    2. Headings
    3. Lists
    4. Tables
    5. Images
    6. Image text translation
    """

    print(
        "\n=========================================="
    )

    print(
        "STARTING DOCX RECONSTRUCTION"
    )

    print(
        "=========================================="
    )

    print(
        f"Input DOCX: "
        f"{original_docx_path}"
    )

    print(
        f"Translated JSON: "
        f"{translated_json_path}"
    )

    print(
        f"Output DOCX: "
        f"{output_docx_path}"
    )

    # ========================================================
    # CHECK FILES
    # ========================================================

    if not os.path.exists(
        original_docx_path
    ):

        raise FileNotFoundError(
            f"Original DOCX not found: "
            f"{original_docx_path}"
        )

    if not os.path.exists(
        translated_json_path
    ):

        raise FileNotFoundError(
            f"Translated JSON not found: "
            f"{translated_json_path}"
        )

    # ========================================================
    # LOAD DOCUMENT
    # ========================================================

    document = Document(
        original_docx_path
    )

    # ========================================================
    # LOAD JSON
    # ========================================================

    with open(
        translated_json_path,
        "r",
        encoding="utf-8"
    ) as file:

        translated_data = json.load(
            file
        )

    elements = translated_data.get(
        "elements",
        []
    )

    print(
        f"Total JSON elements: "
        f"{len(elements)}"
    )

    # ========================================================
    # TEMP DIRECTORY
    # ========================================================

    base_dir = os.path.dirname(
        os.path.abspath(
            original_docx_path
        )
    )

    temp_folder = os.path.join(
        base_dir,
        "temp",
        os.path.splitext(
            os.path.basename(
                original_docx_path
            )
        )[0]
    )

    os.makedirs(
        temp_folder,
        exist_ok=True
    )

    print(
        f"Working image folder: "
        f"{temp_folder}"
    )

    # ========================================================
    # 1. PARAGRAPHS
    # ========================================================

    reconstruct_paragraphs(
        document,
        elements
    )

    # ========================================================
    # 2. TABLES
    # ========================================================

    reconstruct_tables(
        document,
        elements
    )

    # ========================================================
    # 3. IMAGES
    # ========================================================

    reconstructed_images = (
        reconstruct_images(
            original_docx_path,
            elements,
            temp_folder
        )
    )

    # ========================================================
    # SAVE TEXT/TABLE RECONSTRUCTION
    # ========================================================

    output_dir = os.path.dirname(
        os.path.abspath(
            output_docx_path
        )
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    document.save(
        output_docx_path
    )

    print(
        "\nText/table reconstruction saved."
    )

    # ========================================================
    # 4. REPLACE IMAGES
    # ========================================================

    if reconstructed_images:

        print(
            "\n========== REPLACING DOCX IMAGES =========="
        )

        success = replace_images_in_docx(
            output_docx_path,
            output_docx_path,
            reconstructed_images
        )

        if success:

            print(
                "Final DOCX updated with "
                "reconstructed images."
            )

    else:

        print(
            "No reconstructed images to replace."
        )

    # ========================================================
    # FINAL
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "DOCX RECONSTRUCTION COMPLETED"
    )

    print(
        f"Output: "
        f"{output_docx_path}"
    )

    print(
        "=========================================="
    )

    return output_docx_path
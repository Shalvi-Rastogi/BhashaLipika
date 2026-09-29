import json
import os

import fitz


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

FONT_DIR = os.path.join(
    BASE_DIR,
    "assets",
    "fonts"
)


def find_font(target_language):
    """
    Find a Unicode font suitable for Hindi/Marathi.
    """

    possible_fonts = []

    if target_language.lower() in ["hi", "mr"]:

        possible_fonts = [
            os.path.join(
                FONT_DIR,
                "Nirmala.ttf"
            ),
            os.path.join(
                FONT_DIR,
                "Mangal.ttf"
            ),
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\mangal.ttf"
        ]

    for font_path in possible_fonts:

        if os.path.exists(font_path):
            return font_path

    return None


def reconstruct_native_pdf(
    original_pdf_path,
    translated_json_path,
    output_pdf_path,
    target_language="hi"
):

    with open(
        translated_json_path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    original_document = fitz.open(
        original_pdf_path
    )

    output_document = fitz.open()

    font_path = find_font(
        target_language
    )

    print(
        f"[PDF] Font selected: {font_path}"
    )

    try:

        for page_data in data.get(
            "pages",
            []
        ):

            width = float(
                page_data.get(
                    "width",
                    595
                )
            )

            height = float(
                page_data.get(
                    "height",
                    842
                )
            )

            page = output_document.new_page(
                width=width,
                height=height
            )

            # White background
            page.draw_rect(
                fitz.Rect(
                    0,
                    0,
                    width,
                    height
                ),
                color=(1, 1, 1),
                fill=(1, 1, 1)
            )

            for element in page_data.get(
                "elements",
                []
            ):

                if element.get(
                    "type"
                ) != "text":
                    continue

                text = (
                    element.get(
                        "translated_text"
                    )
                    or
                    element.get(
                        "original_text",
                        ""
                    )
                )

                if not text.strip():
                    continue

                bbox = element.get(
                    "bbox",
                    [0, 0, 0, 0]
                )

                x0, y0, x1, y1 = [
                    float(v)
                    for v in bbox
                ]

                font_info = element.get(
                    "font",
                    {}
                )

                font_size = float(
                    font_info.get(
                        "font_size",
                        10
                    )
                )

                # -----------------------------------------
                # PDF text insertion
                # -----------------------------------------

                kwargs = {
                    "fontsize": font_size,
                    "fontname": "helv"
                }

                # Use Unicode font if available
                if font_path:

                    try:

                        kwargs = {
                            "fontsize": font_size,
                            "fontfile": font_path
                        }

                    except Exception:
                        pass

                # PyMuPDF uses top-left coordinates.
                # Text baseline needs adjustment.
                point = fitz.Point(
                    x0,
                    y1 - 1
                )

                try:

                    page.insert_text(
                        point,
                        text,
                        **kwargs
                    )

                except Exception as e:

                    print(
                        f"[PDF] Could not insert text "
                        f"'{text[:30]}': {e}"
                    )

                    # Fallback to Helvetica
                    try:

                        page.insert_text(
                            point,
                            text,
                            fontsize=font_size,
                            fontname="helv"
                        )

                    except Exception:
                        pass

        os.makedirs(
            os.path.dirname(output_pdf_path),
            exist_ok=True
        )

        output_document.save(
            output_pdf_path
        )

    finally:

        output_document.close()
        original_document.close()

    print(
        f"[PDF] Reconstruction completed: "
        f"{output_pdf_path}"
    )

    return output_pdf_path
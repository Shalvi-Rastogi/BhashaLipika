import json
import os
import copy
import zipfile
import xml.etree.ElementTree as ET


# ============================================================
# XML NAMESPACES
# ============================================================

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",

    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",

    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",

    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",

    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


# Register common namespaces so ElementTree does not
# generate unnecessary ns0/ns1 prefixes.

ET.register_namespace(
    "",
    NS["main"]
)

ET.register_namespace(
    "r",
    NS["r"]
)

ET.register_namespace(
    "xdr",
    NS["xdr"]
)

ET.register_namespace(
    "a",
    NS["a"]
)


# ============================================================
# HELPERS
# ============================================================

def qname(namespace, tag):
    return f"{{{namespace}}}{tag}"


def normalize_zip_path(path):

    path = path.replace(
        "\\",
        "/"
    )

    while path.startswith("/"):
        path = path[1:]

    parts = []

    for part in path.split("/"):

        if part == "..":

            if parts:
                parts.pop()

        elif part == "." or part == "":
            continue

        else:
            parts.append(part)

    return "/".join(parts)


def get_relationship_target(
    source_file,
    target
):

    source_dir = os.path.dirname(
        source_file
    )

    if target.startswith("/"):
        return normalize_zip_path(
            target
        )

    return normalize_zip_path(
        os.path.join(
            source_dir,
            target
        )
    )


# ============================================================
# SHEET -> DRAWING MAP
# ============================================================

def get_sheet_drawing_map(
    zip_file
):

    result = {}

    workbook_xml_path = (
        "xl/workbook.xml"
    )

    workbook_rels_path = (
        "xl/_rels/workbook.xml.rels"
    )

    names = zip_file.namelist()

    if workbook_xml_path not in names:
        return result

    if workbook_rels_path not in names:
        return result

    workbook_root = ET.fromstring(
        zip_file.read(
            workbook_xml_path
        )
    )

    workbook_rels_root = ET.fromstring(
        zip_file.read(
            workbook_rels_path
        )
    )

    # --------------------------------------------------------
    # Workbook relationship map
    # --------------------------------------------------------

    workbook_rel_map = {}

    for rel in workbook_rels_root.findall(
        "rel:Relationship",
        NS
    ):

        rel_id = rel.attrib.get(
            "Id"
        )

        target = rel.attrib.get(
            "Target"
        )

        if rel_id and target:

            workbook_rel_map[
                rel_id
            ] = get_relationship_target(
                workbook_xml_path,
                target
            )

    sheets_element = workbook_root.find(
        "main:sheets",
        NS
    )

    if sheets_element is None:
        return result

    # --------------------------------------------------------
    # Every worksheet
    # --------------------------------------------------------

    for sheet in sheets_element.findall(
        "main:sheet",
        NS
    ):

        sheet_name = sheet.attrib.get(
            "name"
        )

        rel_id = sheet.attrib.get(
            qname(
                NS["r"],
                "id"
            )
        )

        if not sheet_name or not rel_id:
            continue

        worksheet_path = workbook_rel_map.get(
            rel_id
        )

        if not worksheet_path:
            continue

        worksheet_rels_path = (
            os.path.dirname(
                worksheet_path
            )
            + "/_rels/"
            + os.path.basename(
                worksheet_path
            )
            + ".rels"
        )

        if worksheet_rels_path not in names:
            continue

        worksheet_xml_root = ET.fromstring(
            zip_file.read(
                worksheet_path
            )
        )

        worksheet_rels_root = ET.fromstring(
            zip_file.read(
                worksheet_rels_path
            )
        )

        worksheet_rel_map = {}

        for rel in worksheet_rels_root.findall(
            "rel:Relationship",
            NS
        ):

            rel_id_2 = rel.attrib.get(
                "Id"
            )

            target = rel.attrib.get(
                "Target"
            )

            if rel_id_2 and target:

                worksheet_rel_map[
                    rel_id_2
                ] = get_relationship_target(
                    worksheet_path,
                    target
                )

        drawing_paths = []

        for drawing in worksheet_xml_root.findall(
            "main:drawing",
            NS
        ):

            drawing_rel_id = drawing.attrib.get(
                qname(
                    NS["r"],
                    "id"
                )
            )

            if not drawing_rel_id:
                continue

            drawing_path = worksheet_rel_map.get(
                drawing_rel_id
            )

            if drawing_path:
                drawing_paths.append(
                    drawing_path
                )

        result[
            sheet_name
        ] = drawing_paths

    return result


# ============================================================
# FIND TEXTBOX SHAPE
# ============================================================

def find_textbox_by_shape_id(
    drawing_root,
    shape_id
):

    for shape in drawing_root.findall(
        ".//xdr:sp",
        NS
    ):

        c_nv_pr = shape.find(
            "xdr:nvSpPr/xdr:cNvPr",
            NS
        )

        if c_nv_pr is None:
            continue

        current_id = c_nv_pr.attrib.get(
            "id"
        )

        if str(current_id) == str(
            shape_id
        ):

            tx_body = shape.find(
                "xdr:txBody",
                NS
            )

            if tx_body is not None:
                return shape

    return None


# ============================================================
# GET FIRST RUN PROPERTIES
# ============================================================

def get_first_run_properties(
    tx_body
):

    first_run = tx_body.find(
        ".//a:r",
        NS
    )

    if first_run is None:
        return None

    r_pr = first_run.find(
        "a:rPr",
        NS
    )

    if r_pr is None:
        return None

    return copy.deepcopy(
        r_pr
    )


# ============================================================
# CREATE TEXT RUN
# ============================================================

def create_text_run(
    text,
    run_properties=None
):

    run = ET.Element(
        qname(
            NS["a"],
            "r"
        )
    )

    if run_properties is not None:

        run.append(
            copy.deepcopy(
                run_properties
            )
        )

    text_element = ET.SubElement(
        run,
        qname(
            NS["a"],
            "t"
        )
    )

    # Important for leading/trailing spaces.
    if (
        text.startswith(" ")
        or text.endswith(" ")
    ):

        text_element.set(
            "{http://www.w3.org/XML/1998/namespace}space",
            "preserve"
        )

    text_element.text = text

    return run


# ============================================================
# REPLACE TEXTBOX CONTENT
# ============================================================

def replace_textbox_text(
    shape,
    translated_text
):

    tx_body = shape.find(
        "xdr:txBody",
        NS
    )

    if tx_body is None:
        return False

    # --------------------------------------------------------
    # Existing paragraphs
    # --------------------------------------------------------

    existing_paragraphs = tx_body.findall(
        "a:p",
        NS
    )

    # --------------------------------------------------------
    # Get formatting from first existing run.
    # This allows the translated text to retain the
    # textbox's original font styling.
    # --------------------------------------------------------

    run_properties = get_first_run_properties(
        tx_body
    )

    # --------------------------------------------------------
    # Split translated content into paragraphs.
    # --------------------------------------------------------

    translated_paragraphs = (
        str(
            translated_text
            if translated_text is not None
            else ""
        )
        .split("\n")
    )

    if not translated_paragraphs:
        translated_paragraphs = [""]

    # ========================================================
    # CASE 1:
    # Existing paragraphs available
    # ========================================================

    if existing_paragraphs:

        # ----------------------------------------------------
        # Use existing paragraphs wherever possible.
        # ----------------------------------------------------

        for index, paragraph_text in enumerate(
            translated_paragraphs
        ):

            if index < len(
                existing_paragraphs
            ):

                paragraph = (
                    existing_paragraphs[
                        index
                    ]
                )

            else:

                # Copy paragraph formatting
                # from first paragraph.
                paragraph = copy.deepcopy(
                    existing_paragraphs[0]
                )

                # Remove all content.
                for child in list(
                    paragraph
                ):

                    if child.tag not in (
                        qname(
                            NS["a"],
                            "pPr"
                        ),
                        qname(
                            NS["a"],
                            "endParaRPr"
                        ),
                    ):

                        paragraph.remove(
                            child
                        )

                tx_body.append(
                    paragraph
                )

            # ------------------------------------------------
            # Preserve paragraph properties.
            # Remove old text/runs.
            # ------------------------------------------------

            for child in list(
                paragraph
            ):

                if child.tag not in (
                    qname(
                        NS["a"],
                        "pPr"
                    ),
                    qname(
                        NS["a"],
                        "endParaRPr"
                    ),
                ):

                    paragraph.remove(
                        child
                    )

            # ------------------------------------------------
            # Add translated run.
            # ------------------------------------------------

            run = create_text_run(
                paragraph_text,
                run_properties
            )

            paragraph.append(
                run
            )

        # ----------------------------------------------------
        # Remove extra original paragraphs.
        # ----------------------------------------------------

        while len(
            tx_body.findall(
                "a:p",
                NS
            )
        ) > len(
            translated_paragraphs
        ):

            paragraphs_now = (
                tx_body.findall(
                    "a:p",
                    NS
                )
            )

            extra = paragraphs_now[-1]

            tx_body.remove(
                extra
            )

    # ========================================================
    # CASE 2:
    # No paragraph existed.
    # ========================================================

    else:

        for paragraph_text in (
            translated_paragraphs
        ):

            paragraph = ET.SubElement(
                tx_body,
                qname(
                    NS["a"],
                    "p"
                )
            )

            run = create_text_run(
                paragraph_text,
                run_properties
            )

            paragraph.append(
                run
            )

    return True


# ============================================================
# UPDATE DRAWING XML
# ============================================================

def update_drawing_xml(
    xml_bytes,
    textbox_updates
):

    try:

        drawing_root = ET.fromstring(
            xml_bytes
        )

    except ET.ParseError as e:

        print(
            f"[XLSX RECONSTRUCTION ERROR] "
            f"Could not parse drawing XML: {e}"
        )

        return xml_bytes, 0

    updated_count = 0

    # --------------------------------------------------------
    # textbox_updates:
    #
    # [
    #   {
    #       "shape_id": "2",
    #       "translated_text": "प्रौद्योगिकी"
    #   }
    # ]
    # --------------------------------------------------------

    for update in textbox_updates:

        shape_id = update.get(
            "shape_id"
        )

        translated_text = update.get(
            "translated_text",
            ""
        )

        if not shape_id:
            continue

        shape = find_textbox_by_shape_id(
            drawing_root,
            shape_id
        )

        if shape is None:

            print(
                f"[XLSX WARNING] "
                f"Textbox shape ID {shape_id} "
                f"not found."
            )

            continue

        success = replace_textbox_text(
            shape,
            translated_text
        )

        if success:

            updated_count += 1

            print(
                f"[XLSX TEXTBOX UPDATED] "
                f"Shape ID: {shape_id}"
            )

    # --------------------------------------------------------
    # Write XML back.
    # --------------------------------------------------------

    new_xml = ET.tostring(
        drawing_root,
        encoding="utf-8",
        xml_declaration=True
    )

    return new_xml, updated_count


# ============================================================
# NORMAL CELL UPDATE
# ============================================================

def update_cell_xml(
    xml_bytes,
    cell_updates
):

    try:

        root = ET.fromstring(
            xml_bytes
        )

    except ET.ParseError:

        return xml_bytes, 0

    updated_count = 0

    update_map = {}

    for update in cell_updates:

        coordinate = update.get(
            "coordinate"
        )

        if not coordinate:
            continue

        translated_text = update.get(
            "translated_text",
            update.get(
                "original_text",
                ""
            )
        )

        update_map[
            coordinate
        ] = translated_text

    if not update_map:
        return xml_bytes, 0

    # --------------------------------------------------------
    # Find cells.
    # --------------------------------------------------------

    for cell in root.findall(
        ".//main:c",
        NS
    ):

        coordinate = cell.attrib.get(
            "r"
        )

        if coordinate not in update_map:
            continue

        new_text = update_map[
            coordinate
        ]

        cell_type = cell.attrib.get(
            "t"
        )

        # ----------------------------------------------------
        # Inline string cell
        # ----------------------------------------------------

        if cell_type == "inlineStr":

            t_element = cell.find(
                "main:is/main:t",
                NS
            )

            if t_element is None:

                is_element = cell.find(
                    "main:is",
                    NS
                )

                if is_element is None:

                    is_element = ET.SubElement(
                        cell,
                        qname(
                            NS["main"],
                            "is"
                        )
                    )

                t_element = ET.SubElement(
                    is_element,
                    qname(
                        NS["main"],
                        "t"
                    )
                )

            t_element.text = str(
                new_text
            )

            updated_count += 1

        # ----------------------------------------------------
        # Shared string
        #
        # We intentionally do not directly modify shared
        # strings here because one shared string may be used
        # by multiple cells.
        # ----------------------------------------------------

        elif cell_type == "s":

            # Leave shared strings unchanged.
            # TextBox processing remains completely safe.
            continue

        # ----------------------------------------------------
        # Normal string cell
        # ----------------------------------------------------

        else:

            value_element = cell.find(
                "main:v",
                NS
            )

            if value_element is not None:

                value_element.text = str(
                    new_text
                )

                # If it was numeric but translation
                # converted it to text, mark as string.
                cell.set(
                    "t",
                    "str"
                )

                updated_count += 1

    if updated_count == 0:
        return xml_bytes, 0

    new_xml = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True
    )

    return new_xml, updated_count


# ============================================================
# MAIN RECONSTRUCTOR
# ============================================================

def reconstruct_xlsx(
    original_file_path,
    translated_json_path,
    output_file_path
):

    print("\n========================================")
    print("XLSX RECONSTRUCTION STARTED")
    print("========================================")

    # ========================================================
    # LOAD TRANSLATED JSON
    # ========================================================

    with open(
        translated_json_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    # ========================================================
    # COLLECT UPDATES
    # ========================================================

    drawing_updates = {}

    cell_updates = {}

    for sheet_data in data.get(
        "sheets",
        []
    ):

        # ----------------------------------------------------
        # Normal cells
        # ----------------------------------------------------

        for cell in sheet_data.get(
            "cells",
            []
        ):

            coordinate = cell.get(
                "coordinate"
            )

            if coordinate:

                cell_updates.setdefault(
                    sheet_data.get(
                        "sheet_name"
                    ),
                    []
                ).append(
                    cell
                )

        # ----------------------------------------------------
        # Floating TextBoxes
        # ----------------------------------------------------

        for textbox in sheet_data.get(
            "textboxes",
            []
        ):

            drawing_file = textbox.get(
                "drawing_file"
            )

            if not drawing_file:
                continue

            drawing_updates.setdefault(
                drawing_file,
                []
            ).append(
                textbox
            )

    print(
        f"[XLSX] Drawings containing updates: "
        f"{len(drawing_updates)}"
    )

    total_textboxes = sum(
        len(items)
        for items in drawing_updates.values()
    )

    print(
        f"[XLSX] TextBoxes to reconstruct: "
        f"{total_textboxes}"
    )

    # ========================================================
    # DIRECT XLSX ZIP RECONSTRUCTION
    # ========================================================
    #
    # IMPORTANT:
    #
    # We DO NOT use:
    #
    #     openpyxl.load_workbook()
    #     wb.save()
    #
    # here.
    #
    # That is what was removing the floating TextBoxes.
    #
    # Instead, we copy the original XLSX package and modify
    # only the required XML files.
    #
    # ========================================================

    with zipfile.ZipFile(
        original_file_path,
        "r"
    ) as source_zip:

        with zipfile.ZipFile(
            output_file_path,
            "w",
            compression=zipfile.ZIP_DEFLATED
        ) as output_zip:

            for item in source_zip.infolist():

                file_name = item.filename

                original_bytes = (
                    source_zip.read(
                        file_name
                    )
                )

                modified_bytes = (
                    original_bytes
                )

                # ====================================================
                # DRAWING XML
                # ====================================================

                if file_name in drawing_updates:

                    print(
                        f"\n[XLSX] Updating drawing: "
                        f"{file_name}"
                    )

                    modified_bytes, count = (
                        update_drawing_xml(
                            original_bytes,
                            drawing_updates[
                                file_name
                            ]
                        )
                    )

                    print(
                        f"[XLSX] TextBoxes updated: "
                        f"{count}"
                    )

                # ====================================================
                # WORKSHEET XML
                # ====================================================

                elif (
                    file_name.startswith(
                        "xl/worksheets/"
                    )
                    and file_name.endswith(
                        ".xml"
                    )
                ):

                    # ------------------------------------------------
                    # We currently update only inline/normal string
                    # cells here.
                    # ------------------------------------------------

                    sheet_name = None

                    # Find matching sheet by comparing
                    # its relationship/drawing information.
                    #
                    # Since TextBox reconstruction is the main
                    # requirement, cell reconstruction is kept
                    # conservative.
                    #
                    # We match sheet XML using workbook mapping.
                    # ------------------------------------------------

                    try:

                        workbook_xml = ET.fromstring(
                            source_zip.read(
                                "xl/workbook.xml"
                            )
                        )

                        workbook_rels = ET.fromstring(
                            source_zip.read(
                                "xl/_rels/workbook.xml.rels"
                            )
                        )

                        workbook_rel_map = {}

                        for rel in workbook_rels.findall(
                            "rel:Relationship",
                            NS
                        ):

                            rel_id = rel.attrib.get(
                                "Id"
                            )

                            target = rel.attrib.get(
                                "Target"
                            )

                            if rel_id and target:

                                workbook_rel_map[
                                    rel_id
                                ] = get_relationship_target(
                                    "xl/workbook.xml",
                                    target
                                )

                        sheets_element = (
                            workbook_xml.find(
                                "main:sheets",
                                NS
                            )
                        )

                        if sheets_element is not None:

                            for sheet in (
                                sheets_element.findall(
                                    "main:sheet",
                                    NS
                                )
                            ):

                                rel_id = sheet.attrib.get(
                                    qname(
                                        NS["r"],
                                        "id"
                                    )
                                )

                                worksheet_path = (
                                    workbook_rel_map.get(
                                        rel_id
                                    )
                                )

                                if worksheet_path == file_name:

                                    sheet_name = (
                                        sheet.attrib.get(
                                            "name"
                                        )
                                    )

                                    break

                    except Exception as e:

                        print(
                            f"[XLSX WARNING] "
                            f"Could not identify worksheet "
                            f"{file_name}: {e}"
                        )

                    if sheet_name in cell_updates:

                        modified_bytes, count = (
                            update_cell_xml(
                                original_bytes,
                                cell_updates[
                                    sheet_name
                                ]
                            )
                        )

                        if count:

                            print(
                                f"[XLSX] "
                                f"{count} cell(s) updated "
                                f"in {sheet_name}"
                            )

                # ====================================================
                # WRITE FILE
                # ====================================================

                output_zip.writestr(
                    item,
                    modified_bytes
                )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if os.path.exists(
        output_file_path
    ):

        file_size = os.path.getsize(
            output_file_path
        )

        print(
            "\n[XLSX] Reconstruction successful."
        )

        print(
            f"[XLSX] Output size: "
            f"{file_size} bytes"
        )

        print(
            f"[XLSX] Output file: "
            f"{output_file_path}"
        )

    else:

        raise FileNotFoundError(
            "Reconstructed XLSX file was not created."
        )

    print("\n========================================")
    print("XLSX RECONSTRUCTION COMPLETED")
    print("========================================")

    return output_file_path
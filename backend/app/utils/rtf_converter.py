import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from app.utils.doc_converter import _get_soffice_path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def convert_rtf_to_docx(rtf_path, output_dir):
    rtf_path = Path(rtf_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    subprocess.run(
        [
            _get_soffice_path(),
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(rtf_path)
        ],
        check=True
    )

    converted_path = (
        output_dir /
        f"{rtf_path.stem}.docx"
    )

    if not converted_path.exists():
        raise FileNotFoundError(
            f"RTF to DOCX conversion failed: {converted_path}"
        )

    return str(converted_path)


def _prepare_docx_for_rtf_export(docx_path, temporary_dir):
    converted_input = Path(temporary_dir) / docx_path.name
    value_attribute = f"{{{W_NS}}}val"
    color_attribute = f"{{{W_NS}}}color"
    fill_attribute = f"{{{W_NS}}}fill"

    with zipfile.ZipFile(docx_path) as source, zipfile.ZipFile(
        converted_input,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as prepared:
        for entry in source.infolist():
            content = source.read(entry.filename)

            if entry.filename.startswith("word/") and entry.filename.endswith(
                ".xml"
            ):
                root = etree.fromstring(
                    content,
                    parser=etree.XMLParser(
                        resolve_entities=False,
                        no_network=True,
                    ),
                )
                changed = False

                for shading in root.iter(f"{{{W_NS}}}shd"):
                    fill = shading.get(fill_attribute)
                    if (
                        shading.get(value_attribute) == "solid"
                        and shading.get(color_attribute) == "auto"
                        and fill
                        and fill != "auto"
                    ):
                        shading.set(value_attribute, "clear")
                        changed = True

                if changed:
                    tree = root.getroottree()
                    content = etree.tostring(
                        root,
                        encoding="UTF-8",
                        xml_declaration=True,
                        standalone=tree.docinfo.standalone,
                    )

            prepared.writestr(entry, content)

    return converted_input


def convert_docx_to_rtf(docx_path, output_dir):
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    with tempfile.TemporaryDirectory(
        prefix="rtf_export_",
        dir=output_dir,
    ) as temporary_dir:
        converted_input = _prepare_docx_for_rtf_export(
            docx_path,
            temporary_dir,
        )

        subprocess.run(
            [
                _get_soffice_path(),
                "--headless",
                "--convert-to",
                "rtf",
                "--outdir",
                str(output_dir),
                str(converted_input)
            ],
            check=True
        )

    converted_path = (
        output_dir /
        f"{docx_path.stem}.rtf"
    )

    if not converted_path.exists():
        raise FileNotFoundError(
            f"DOCX to RTF conversion failed: {converted_path}"
        )

    return str(converted_path)
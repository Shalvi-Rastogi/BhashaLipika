# app/utils/doc_converter.py

import subprocess
from pathlib import Path


def convert_doc_to_docx(doc_path, output_dir):

    doc_path = Path(doc_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(doc_path)
        ],
        check=True
    )

    converted_path = (
        output_dir /
        f"{doc_path.stem}.docx"
    )

    if not converted_path.exists():
        raise FileNotFoundError(
            f"DOC to DOCX conversion failed: "
            f"{converted_path}"
        )

    return str(converted_path)


def convert_docx_to_doc(
    docx_path,
    output_dir
):
    """
    Convert reconstructed DOCX back to legacy DOC.
    """

    docx_path = Path(docx_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "doc:MS Word 97",
            "--outdir",
            str(output_dir),
            str(docx_path)
        ],
        check=True
    )

    converted_path = (
        output_dir /
        f"{docx_path.stem}.doc"
    )

    if not converted_path.exists():

        raise FileNotFoundError(
            f"DOCX to DOC conversion failed: "
            f"{converted_path}"
        )

    return str(converted_path)
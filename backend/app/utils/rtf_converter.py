import subprocess
import shutil
from pathlib import Path


def _get_soffice_path():
    candidates = [
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate

    raise FileNotFoundError(
        "LibreOffice was not found. "
        "Install LibreOffice or set the SOFFICE_PATH."
    )


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


def convert_docx_to_rtf(docx_path, output_dir):
    docx_path = Path(docx_path)
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
            "rtf",
            "--outdir",
            str(output_dir),
            str(docx_path)
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
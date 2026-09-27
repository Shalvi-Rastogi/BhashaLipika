import subprocess
from pathlib import Path

from app.utils.doc_converter import _get_soffice_path


def convert_xls_to_xlsx(input_file: str, output_dir: str) -> str:
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            _get_soffice_path(),
            "--headless",
            "--convert-to",
            "xlsx:Calc MS Excel 2007 XML",
            "--outdir",
            str(output_path),
            str(input_path),
        ],
        check=True,
    )

    converted_file = output_path / f"{input_path.stem}.xlsx"

    if not converted_file.exists():
        raise RuntimeError("XLS to XLSX conversion failed.")

    return str(converted_file)


def convert_xlsx_to_xls(input_file: str, output_dir: str) -> str:
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    output_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            _get_soffice_path(),
            "--headless",
            "--convert-to",
            "xls:MS Excel 97",
            "--outdir",
            str(output_path),
            str(input_path),
        ],
        check=True,
    )

    converted_file = output_path / f"{input_path.stem}.xls"

    if not converted_file.exists():
        raise RuntimeError("XLSX to XLS conversion failed.")

    return str(converted_file)
import zipfile
from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NS = {
    "w": W_NS
}


def extract_textboxes_from_docx(docx_path):
    """
    Extract text contained inside Word textboxes/shapes.

    Returns:
        [
            {
                "id": 1,
                "text": "...",
                "paragraphs": [...]
            }
        ]
    """

    textboxes = []

    with zipfile.ZipFile(docx_path, "r") as docx:

        if "word/document.xml" not in docx.namelist():
            return textboxes

        xml_data = docx.read("word/document.xml")

    root = etree.fromstring(xml_data)

    textbox_nodes = root.xpath(
        ".//w:txbxContent",
        namespaces=NS
    )

    for index, textbox in enumerate(textbox_nodes, start=1):

        paragraphs = []

        for paragraph in textbox.xpath(
            ".//w:p",
            namespaces=NS
        ):

            parts = []

            for node in paragraph.iter():

                if node.tag == f"{{{W_NS}}}t":
                    parts.append(node.text or "")

                elif node.tag == f"{{{W_NS}}}tab":
                    parts.append("\t")

            text = "".join(parts)

            if text.strip():
                paragraphs.append(text)

        full_text = "\n".join(paragraphs)

        if not full_text.strip():
            continue

        textboxes.append({
            "id": index,
            "type": "textbox",
            "text": full_text,
            "paragraphs": paragraphs
        })

    return textboxes
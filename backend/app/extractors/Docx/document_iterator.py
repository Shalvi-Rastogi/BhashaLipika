from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table


def iter_block_items(doc):
    """
    Yield paragraphs and tables in the original order
    in which they appear in the document.
    """

    parent = doc.element.body

    for child in parent.iterchildren():

        if isinstance(child, CT_P):
            yield Paragraph(child, doc)

        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)
def extract_text_from_shape(shape, shape_index):
    """Extracts text from a PowerPoint shape if it contains a text frame."""
    text_content = []
    for paragraph in shape.text_frame.paragraphs:
        text = paragraph.text.strip()
        if text:
            # FIX: C-DAC API Hallucination rokne ke liye ALL CAPS ko Title Case mein badlo
            if text.isupper():
                text = text.title()
            text_content.append(text)
    
    if text_content:
        return {
            "shape_index": shape_index,
            "type": "text_frame",
            "original_text": "\n".join(text_content),
            "translated_text": ""
        }
    return None
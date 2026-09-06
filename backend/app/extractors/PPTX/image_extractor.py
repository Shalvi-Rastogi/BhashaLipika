import os

def extract_image(shape, shape_index, slide_number, output_dir):
    """Extracts image binary from shape and saves it to output directory."""
    try:
        image = shape.image
        image_bytes = image.blob
        image_ext = image.ext
        
        image_filename = f"slide_{slide_number}_shape_{shape_index}.{image_ext}"
        image_path = os.path.join(output_dir, image_filename)
        
        with open(image_path, "wb") as f:
            f.write(image_bytes)
            
        return {
            "shape_index": shape_index,
            "type": "image",
            "image_path": image_path,
            "original_text": "", # Can be updated later using OCR
            "translated_text": ""
        }
    except Exception as e:
        print(f"Error extracting image at slide {slide_number}, shape {shape_index}: {e}")
        return None
import re


_ENGLISH_TO_HINDI_IMAGE_OVERRIDES = {
    "strengths": "ताकत",
    "dedicated": "समर्पित",
    "creative": "रचनात्मक",
    "flexible": "लचीला",
    "resourceful": "साधन-संपन्न",
    "problem solving skills": "समस्या-समाधान कौशल",
    "ability to work under pressure": "दबाव में काम करने की क्षमता",
    "ability t0 work under pressure": "दबाव में काम करने की क्षमता",
    "time management skills": "समय प्रबंधन कौशल",
    "team player": "टीम के साथ मिलकर काम करने में कुशल",
}


def get_image_translation_override(text, source_language, target_language):
    if (source_language, target_language) != ("eng-latn", "hin-deva"):
        return None

    normalized_text = re.sub(r"[\W_]+", " ", text.casefold()).strip()
    return _ENGLISH_TO_HINDI_IMAGE_OVERRIDES.get(normalized_text)

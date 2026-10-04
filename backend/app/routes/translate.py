from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.html_translator import translate_html

from app.routes.upload import translate_text, LANGUAGE_MAP

router = APIRouter()

class HTMLTranslationRequest(BaseModel):
    html: str
    target_language: str


@router.post("/translate-html")
def translate_html_content(request: HTMLTranslationRequest):

    if not request.html.strip():
        raise HTTPException(
            status_code=400,
            detail="HTML content cannot be empty."
        )

    if request.target_language not in LANGUAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail="Unsupported target language."
        )

    tgt_lang_code = LANGUAGE_MAP[
        request.target_language
    ]

    translated_html = translate_html(
        request.html,
        translate_text,
        "eng-latn",
        tgt_lang_code
    )

    return {
        "translated_html": translated_html
    }

class TranslateRequest(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str


@router.post("/translate")
def translate_direct(request: TranslateRequest):

    if not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter some text to translate."
        )

    source_language = request.source_language.lower().strip()
    target_language = request.target_language.lower().strip()

    src_lang = LANGUAGE_MAP.get(source_language)
    tgt_lang = LANGUAGE_MAP.get(target_language)

    if not src_lang:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source language: {source_language}"
        )

    if not tgt_lang:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language: {target_language}"
        )

    translated_text = translate_text(
        request.text,
        src_lang,
        tgt_lang
    )

    return {
        "translated_text": translated_text,
        "source_language": src_lang,
        "source_language_code": src_lang,
        "target_language": target_language,
        "target_language_code": tgt_lang
    }
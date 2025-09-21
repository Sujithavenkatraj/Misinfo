from google import genai
import google.generativeai as genai
import os, json, shutil
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Optional
from PIL import Image
import pytesseract
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # ensure consistent language detection

# Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Check if Tesseract is installed
TESSERACT_PATH = shutil.which("tesseract")
if not TESSERACT_PATH:
    print("⚠️ Warning: Tesseract is not installed or not in PATH. OCR features may fail.")
else:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Language mapping (ISO -> Tesseract code)
LANG_MAP = {
    "en": "eng",
    "hi": "hin",
    "ta": "tam",
    "te": "tel",
    "ml": "mal",
    "bn": "ben",
    "gu": "guj",
    "kn": "kan",
    "mr": "mar",
    "pa": "pan"
}

# -------------------------------
# Schema
# -------------------------------
class AnalysisSchema(BaseModel):
    verdict: str
    confidence: float
    evidence: List[str]
    when: Optional[str] = None
    where: Optional[str] = None
    why: Optional[str] = None
    how: Optional[str] = None
    real_platform_id: Optional[str] = None
    sources: List[str] = []
    summary: str
    guidelines: List[str] = []


# -------------------------------
# Detect Language
# -------------------------------
def detect_language(text: str) -> str:
    """Detect language code from text, fallback to English."""
    try:
        lang = detect(text)
        return lang
    except:
        return "en"


# -------------------------------
# Text Analysis
# -------------------------------
def analyze_content_text(text: str, model="gemini-2.0-flash-001"):
    lang = detect_language(text)

    prompt = (
        "You are an expert fact-checker and misinformation analyst. "
        "Classify the following as 'true', 'fake', or 'uncertain'. "
        "If fake, explain when/where/why/how. "
        "If true, list sources and real_platform_id if relevant. "
        "Provide a concise summary. "
        "⚠️ Generate 3 education tips tailored to THIS TEXT. "
        f"Always respond in the same language as the input (detected: {lang}).\n\n"
        f"CONTENT:\n{text}\n\nReturn JSON matching the schema."
    )

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=AnalysisSchema
    )
    resp = client.models.generate_content(model=model, contents=prompt, config=config)
    return json.loads(resp.text)


# -------------------------------
# Image + OCR Analysis
# -------------------------------
def analyze_image_with_ocr(image_path: str, model="gemini-2.0-flash-001"):
    extracted_text, lang_code = "", "en"

    if TESSERACT_PATH:
        try:
            # Run OCR first with multilingual model
            extracted_text = pytesseract.image_to_string(
                Image.open(image_path),
                lang="eng+tam+hin+tel+mal+ben+guj+kan+mar+pan"
            ).strip()
            if extracted_text:
                lang_code = detect_language(extracted_text)
        except Exception as e:
            print(f"⚠️ OCR failed, continuing with image only: {e}")
    else:
        print("⚠️ Tesseract not installed. Skipping OCR, analyzing image only.")

    # Upload image to Gemini
    file_obj = client.files.upload(file=image_path)

    contents = [
        "You are an expert misinformation analyst. "
        "Classify this image (and OCR text if present) as 'true', 'fake', or 'uncertain'. "
        "If fake, explain when/where/why/how. "
        "If true, list sources and real_platform_id if relevant. "
        "Provide a concise summary. "
        "⚠️ Generate 3 education tips tailored to THIS IMAGE. "
        f"Always respond in the same language as the input (detected: {lang_code})."
    ]
    if extracted_text:
        contents.append(f"OCR TEXT:\n{extracted_text}")
    contents.append(file_obj)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=AnalysisSchema
    )
    resp = client.models.generate_content(model=model, contents=contents, config=config)
    return json.loads(resp.text)

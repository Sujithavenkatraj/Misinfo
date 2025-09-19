import os, requests, uuid
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from .utils import extract_platform_id
from ai_misinfo.genai_client import analyze_content_text, analyze_image_with_ocr, detect_language
from ai_misinfo.firebase_client import save_analysis, get_all_analyses
from ai_misinfo.factcheck_client import factcheck_search


# -------------------------------
# Frontend Home Page
# -------------------------------
def home(request):
    """Render the analyzer form page."""
    return render(request, "analyze.html")


# -------------------------------
# Dashboard Page
# -------------------------------
def dashboard(request):
    """Show list of past analyses from Firebase with optional verdict filter."""
    verdict_filter = request.GET.get("verdict")  # e.g. ?verdict=Fake
    analyses = get_all_analyses(limit=100)  # newest first from firebase_client

    if verdict_filter:
        analyses = [
            a for a in analyses
            if a.get("status_text", "").lower() == verdict_filter.lower()
        ]

    return render(
        request,
        "dashboard.html",
        {"analyses": analyses, "verdict_filter": verdict_filter or "All"}
    )


# -------------------------------
# Helper: Human-friendly output
# -------------------------------
def make_human_friendly(result: dict, input_type: str = "text", lang: str = "en") -> dict:
    """Format raw AI result into user-friendly fields with dynamic education tips."""

    verdict = (result.get("verdict") or "").lower()
    summary = result.get("summary", "")

    # Verdict labels remain short & translatable if needed
    if verdict == "true":
        status_text, brief = "Real", summary
    elif verdict == "fake":
        status_text, brief = "Fake", summary
    else:
        status_text, brief = "Uncertain", summary

    # Prefer Gemini’s localized tips
    edu = result.get("guidelines")

    # Fallback defaults (English only if Gemini gave none)
    if not edu:
        if input_type == "text":
            edu = [
                "Cross-check claims with multiple trusted sources.",
                "Be cautious of emotional or exaggerated language.",
                "Don’t trust forwarded messages blindly."
            ]
        elif input_type == "url":
            edu = [
                "Check the site's domain carefully.",
                "Compare with reputed outlets.",
                "Don’t rely only on the headline; read the article."
            ]
        elif input_type == "image":
            edu = [
                "Run a reverse image search to check origins.",
                "Look for watermarks or edits.",
                "Be careful of viral memes lacking context."
            ]

    result["status_text"] = status_text
    result["brief_summary"] = brief
    result["education"] = edu
    result["language"] = lang
    return result


# -------------------------------
# API Endpoint
# -------------------------------
class AnalyzeAPIView(APIView):
    """Analyze text, URLs, or images for misinformation."""

    def post(self, request):
        itype = request.data.get("input_type")
        content_text, platform_id, lang = None, None, "en"

        # --- URL ---
        if itype == "url":
            url = request.data.get("url", "")
            if not url:
                return Response({"error": "url required"}, status=400)
            try:
                r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")

                if soup.find("article"):
                    content_text = soup.find("article").get_text(separator="\n").strip()
                else:
                    og = (
                        soup.find("meta", property="og:description")
                        or soup.find("meta", attrs={"name": "description"})
                    )
                    content_text = (
                        og["content"] if og and og.get("content") else soup.get_text()
                    )[:4000]

                _, platform_id = extract_platform_id(url)
                if content_text:
                    lang = detect_language(content_text)

            except Exception as e:
                return Response({"error": "fetch error", "details": str(e)}, status=500)

        # --- Text ---
        elif itype == "text":
            content_text = request.data.get("text", "")
            if not content_text:
                return Response({"error": "text required"}, status=400)
            lang = detect_language(content_text)

        # --- Image ---
        elif itype == "image":
            file = request.FILES.get("image")
            if not file:
                return Response({"error": "image file required"}, status=400)

            tmp_path = f"/tmp/{uuid.uuid4().hex}_{file.name}"
            with open(tmp_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)

            try:
                analysis = analyze_image_with_ocr(tmp_path)
                lang = detect_language(analysis.get("summary", "") or "")
            except Exception as e:
                return Response({"error": "image analysis failed", "details": str(e)}, status=500)
            finally:
                try:
                    os.remove(tmp_path)
                except:
                    pass

            analysis = make_human_friendly(analysis, input_type="image", lang=lang)
            if analysis["status_text"] in ["Fake", "Uncertain"]:
                analysis["factcheck_links"] = factcheck_search(analysis.get("summary", ""))

            save_analysis(analysis)
            return Response(analysis)

        else:
            return Response({"error": "invalid input_type"}, status=400)

        # --- Run analysis (text or url) ---
        try:
            analysis = analyze_content_text(content_text)
        except Exception as e:
            return Response({"error": "analysis error", "details": str(e)}, status=500)

        if platform_id:
            analysis["real_platform_id"] = platform_id

        analysis = make_human_friendly(analysis, input_type=itype, lang=lang)

        if analysis["status_text"] in ["Fake", "Uncertain"]:
            analysis["factcheck_links"] = factcheck_search(analysis.get("summary", ""))

        save_analysis(analysis)
        return Response(analysis)

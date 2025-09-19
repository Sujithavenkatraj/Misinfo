# factcheck_client.py
import os, requests

FACTCHECK_API_KEY = os.getenv("FACTCHECK_API_KEY", os.getenv("GEMINI_API_KEY"))

def factcheck_search(query: str, max_results=3):
    """
    Query Google Fact Check API with a search term.
    Returns a list of fact-check results.
    """
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": query,
        "key": FACTCHECK_API_KEY,
        "pageSize": max_results
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()
        results = []
        for claim in data.get("claims", []):
            text = claim.get("text", "")
            for review in claim.get("claimReview", []):
                results.append({
                    "title": review.get("title"),
                    "publisher": review.get("publisher", {}).get("name"),
                    "url": review.get("url"),
                    "text": text,
                    "rating": review.get("textualRating")
                })
        return results
    except Exception:
        return []

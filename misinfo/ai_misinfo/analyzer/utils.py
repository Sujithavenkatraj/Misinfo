# analyzer/utils.py
import re
from urllib.parse import urlparse, parse_qs

def extract_platform_id(url: str):
    """Return tuple (platform, id) or (None, None)"""
    if not url: return (None, None)
    host = urlparse(url).netloc.lower()
    # X / Twitter
    m = re.search(r"twitter\.com|x\.com", host)
    if m:
        # path like /user/status/1234567890
        path = urlparse(url).path
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[-2] == "status":
            return ("x", parts[-1])
    # youtube
    if "youtube.com" in host or "youtu.be" in host:
        # handle watch?v= or youtu.be/ID
        qs = parse_qs(urlparse(url).query)
        if "v" in qs:
            return ("youtube", qs["v"][0])
        else:
            p = urlparse(url).path.strip("/")
            if p:
                return ("youtube", p)
    # instagram
    if "instagram.com" in host:
        parts = urlparse(url).path.strip("/").split("/")
        if parts:
            return ("instagram", parts[0])
    return (None, None)

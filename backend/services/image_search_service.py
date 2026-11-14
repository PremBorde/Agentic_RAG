import re
import urllib.parse
import logging
import asyncio
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("image_search_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# User-Agent header for Wikimedia API and external HTTP requests
HTTP_HEADERS = {
    "User-Agent": "PersonalAIAgentStudio/3.0 (Educational Agentic Workspace; +https://github.com/agent-studio)"
}


from backend.services.web_search_service import clean_source_domain

COMMON_TECH_TYPOS = {
    "antropic": "anthropic",
    "nividia": "nvidia",
    "nvidea": "nvidia",
    "opena": "openai",
    "gogle": "google",
    "alphbet": "alphabet",
    "macbbook": "macbook"
}

def normalize_image_query(q: str) -> str:
    """Corrects common typos in entities and strips conversational noise."""
    tokens = q.strip().split()
    corrected = [COMMON_TECH_TYPOS.get(w.lower(), w) for w in tokens]
    return " ".join(corrected)

def is_image_result_relevant(title: str, url: str, query: str) -> bool:
    """
    Validates that an image search result contains at least one substantive keyword
    from the user query, preventing completely unrelated index hits (e.g. GarageBand for CEO).
    """
    stop_words = {
        "the", "and", "for", "with", "show", "image", "images", 
        "photo", "photos", "picture", "pictures", "diagram", "diagrams",
        "about", "from", "that", "this", "some"
    }
    tokens = [w for w in re.findall(r'[a-zA-Z0-9]+', query.lower()) if len(w) > 2 and w not in stop_words]
    if not tokens:
        return True
    
    haystack = f"{title.lower()} {url.lower()}"
    return any(t in haystack for t in tokens)


def _search_ddgs(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    Retrieves web images using duckduckgo_search / ddgs.
    Returns standardized image records.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("[IMAGE_SEARCH] ddgs/duckduckgo_search library not found.")
            return []

    results: List[Dict[str, Any]] = []
    try:
        with DDGS(timeout=5) as ddgs_client:
            raw_results = list(ddgs_client.images(
                query,
                region="wt-wt",
                safesearch="moderate",
                max_results=max_results * 2  # fetch extra to allow for relevance filtering
            ))

        for item in raw_results:
            img_url = item.get("image")
            thumb_url = item.get("thumbnail") or img_url
            if not img_url:
                continue

            page_url = item.get("url") or img_url
            source_domain = item.get("source") or clean_source_domain(page_url)
            title = (item.get("title") or "Visual Reference").strip()

            # Filter out completely unrelated search results
            if not is_image_result_relevant(title, page_url, query):
                logger.debug(f"[IMAGE_SEARCH] Dropping irrelevant hit: '{title}' for query '{query}'")
                continue

            results.append({
                "title": title,
                "image": img_url,
                "thumbnail": thumb_url,
                "url": page_url,
                "source": source_domain,
                "width": item.get("width"),
                "height": item.get("height"),
                "license": "Web Source",
                "author": None
            })

            if len(results) >= max_results:
                break
    except Exception as e:
        logger.warning(f"[IMAGE_SEARCH] DDGS image search failed: {e}")

    return results


def _search_wikimedia_commons(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """
    Public domain & Creative Commons fallback using Wikimedia Commons API.
    Especially effective for diagrams, science, maps, architecture, and educational visuals.
    """
    results: List[Dict[str, Any]] = []
    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": max_results,
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": 640,
            "format": "json"
        }
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params=params,
            headers=HTTP_HEADERS,
            timeout=4.5
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        pages = data.get("query", {}).get("pages", {})

        for _, page in pages.items():
            image_info_list = page.get("imageinfo", [])
            if not image_info_list:
                continue

            info = image_info_list[0]
            raw_title = page.get("title", "")
            # Clean "File:" prefix and file extension
            clean_title = re.sub(r"^File:\s*", "", raw_title, flags=re.IGNORECASE)
            clean_title = re.sub(r"\.[a-zA-Z0-9]+$", "", clean_title).replace("_", " ").strip()

            full_img_url = info.get("url")
            thumb_url = info.get("thumburl") or full_img_url
            page_url = info.get("descriptionurl") or full_img_url

            ext_meta = info.get("extmetadata", {})
            license_name = ext_meta.get("LicenseShortName", {}).get("value", "CC / Public Domain")
            artist_raw = ext_meta.get("Artist", {}).get("value")
            # Strip HTML tags if present in artist metadata
            clean_artist = re.sub(r"<[^>]+>", "", artist_raw).strip() if artist_raw else None

            if full_img_url:
                results.append({
                    "title": clean_title or "Wikimedia Visual",
                    "image": full_img_url,
                    "thumbnail": thumb_url,
                    "url": page_url,
                    "source": "commons.wikimedia.org",
                    "width": info.get("width"),
                    "height": info.get("height"),
                    "license": license_name,
                    "author": clean_artist
                })
    except Exception as e:
        logger.warning(f"[IMAGE_SEARCH] Wikimedia Commons search failed: {e}")

    return results


def search_web_images(
    query: str, 
    max_results: int = 6, 
    prefer_diagrams: bool = False
) -> Dict[str, Any]:
    """
    Searches web images with primary and fallback providers.
    - If prefer_diagrams is True and 'diagram' is not in query, appends 'diagram'.
    - Primary provider: DuckDuckGo / Bing CDN.
    - Fallback provider: Wikimedia Commons (Creative Commons / Public Domain).
    """
    clean_query = query.strip()
    if not clean_query:
        return {"query": "", "images": [], "provider": "none", "count": 0}

    # Normalize entity typos (e.g. 'antropic' -> 'anthropic')
    search_term = normalize_image_query(clean_query)
    if prefer_diagrams and not any(k in search_term.lower() for k in ["diagram", "schematic", "chart", "figure", "illustration"]):
        search_term = f"{search_term} diagram"

    logger.info(f"[IMAGE_SEARCH] Initiating search for query: '{search_term}' (limit: {max_results})")

    # Step 1: Try Primary Provider (DuckDuckGo Images)
    images = _search_ddgs(search_term, max_results=max_results)
    provider_used = "DuckDuckGo / Bing"

    # Step 2: If primary returns no results or fails, seamlessly fall back to Wikimedia Commons
    if not images:
        logger.info(f"[IMAGE_SEARCH] Primary provider returned 0 results. Falling back to Wikimedia Commons...")
        images = _search_wikimedia_commons(search_term, max_results=max_results)
        provider_used = "Wikimedia Commons"

    logger.info(f"[IMAGE_SEARCH] Retrieved {len(images)} images via {provider_used}")

    return {
        "query": clean_query,
        "search_term": search_term,
        "images": images,
        "provider": provider_used,
        "count": len(images)
    }


async def search_web_images_async(
    query: str, 
    max_results: int = 6, 
    prefer_diagrams: bool = False,
    timeout: float = 6.0
) -> Dict[str, Any]:
    """Asynchronous wrapper for search_web_images with strict execution timeout."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(search_web_images, query, max_results, prefer_diagrams),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"[IMAGE_SEARCH] Search timed out after {timeout}s for query: '{query}'")
        return {
            "query": query,
            "search_term": query,
            "images": [],
            "provider": "timeout",
            "count": 0,
            "error": "Image search timed out"
        }
    except Exception as e:
        logger.error(f"[IMAGE_SEARCH] Async search error: {e}")
        return {
            "query": query,
            "search_term": query,
            "images": [],
            "provider": "error",
            "count": 0,
            "error": str(e)
        }


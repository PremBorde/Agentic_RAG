"""
Web Search Service for Personal AI Agent Studio.
Provides structured live web & news retrieval with timeframe support,
publisher domain extraction, honest error handling, and prompt context formatting.
"""

import re
import urllib.parse
import logging
import asyncio
from typing import List, Dict, Any, Optional

logger = logging.getLogger("web_search_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def clean_source_domain(url: str, default: str = "Web Source") -> str:
    """Extracts a clean, readable hostname without www. prefix."""
    if not url:
        return default
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc or ""
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or default
    except Exception:
        return default


def get_timeframe_label(timeframe: Optional[str]) -> str:
    """Returns a user-friendly label for DDGS timelimit codes."""
    if not timeframe:
        return ""
    mapping = {
        "d": "Last 24 hours",
        "w": "Last 7 days",
        "m": "Last 30 days",
        "y": "Past year"
    }
    return mapping.get(timeframe.lower(), f"Timeframe: {timeframe}")


def search_web_structured(
    query: str, 
    timeframe: Optional[str] = None, 
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Executes live web/news search and returns structured records with:
    - title (headline)
    - snippet (summary)
    - url (original article link)
    - source (publisher domain/name)
    - date (publication date or timeframe indicator)
    """
    clean_q = query.strip()
    if not clean_q:
        return {
            "status": "error",
            "query": "",
            "timeframe": timeframe,
            "timeframe_label": "",
            "results": [],
            "provider": "None",
            "error": "Empty search query"
        }

    logger.info(f"[WEB_SEARCH] Executing search for: '{clean_q}' (timeframe: {timeframe})")
    results: List[Dict[str, Any]] = []
    tf_label = get_timeframe_label(timeframe)

    # 1. Primary Strategy: DuckDuckGoSearchResults (via langchain_community or ddgs)
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        ddg_tool = DuckDuckGoSearchResults(max_results=max_results)
        
        # If timeframe specified, append timeframe context to query if not already present
        search_term = clean_q
        if timeframe == "w" and not any(w in clean_q.lower() for w in ["week", "7 days"]):
            search_term = f"{clean_q} this week"
        elif timeframe == "d" and not any(w in clean_q.lower() for w in ["today", "24 hours"]):
            search_term = f"{clean_q} today"

        raw_output = ddg_tool.invoke(search_term)
        if raw_output and isinstance(raw_output, str) and "snippet:" in raw_output:
            pattern = re.compile(r'snippet:\s*(.*?),\s*title:\s*(.*?),\s*link:\s*(https?://[^\s,\]]+)', re.DOTALL)
            for m in pattern.finditer(raw_output):
                snip = m.group(1).strip()
                t_str = m.group(2).strip()
                link = m.group(3).strip()
                domain = clean_source_domain(link)
                results.append({
                    "title": t_str,
                    "snippet": snip,
                    "url": link,
                    "source": domain,
                    "date": tf_label if tf_label else ""
                })
    except Exception as e:
        logger.warning(f"[WEB_SEARCH] DuckDuckGoSearchResults encountered: {e}")

    # 2. Secondary Strategy: DDGS news or text
    if not results:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                DDGS = None

        if DDGS is not None:
            try:
                with DDGS(timeout=5) as ddgs_client:
                    is_news = any(w in clean_q.lower() for w in ["news", "headline", "breaking", "update", "story"])
                    if is_news:
                        raw_news = []
                        try:
                            if timeframe:
                                raw_news = list(ddgs_client.news(clean_q, timelimit=timeframe, max_results=max_results))
                            if not raw_news:
                                raw_news = list(ddgs_client.news(clean_q, max_results=max_results))
                        except Exception:
                            raw_news = []

                        for item in raw_news:
                            d_str = item.get("date", "").split("T")[0] if item.get("date") else tf_label
                            link = item.get("url") or item.get("link") or ""
                            results.append({
                                "title": item.get("title", "").strip(),
                                "snippet": item.get("body", "").strip(),
                                "url": link,
                                "source": item.get("source") or clean_source_domain(link),
                                "date": d_str
                            })

                    if not results:
                        raw_text = []
                        try:
                            if timeframe:
                                raw_text = list(ddgs_client.text(clean_q, timelimit=timeframe, max_results=max_results))
                            if not raw_text:
                                raw_text = list(ddgs_client.text(clean_q, max_results=max_results))
                        except Exception:
                            raw_text = []

                        for item in raw_text:
                            link = item.get("href") or item.get("link") or ""
                            results.append({
                                "title": item.get("title", "").strip(),
                                "snippet": item.get("body", "").strip(),
                                "url": link,
                                "source": clean_source_domain(link),
                                "date": tf_label if tf_label else ""
                            })
            except Exception as e:
                logger.warning(f"[WEB_SEARCH] DDGS direct client encountered: {e}")

    # 3. Tertiary Fallback: DuckDuckGoSearchRun (unstructured fallback)
    if not results:
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            run_tool = DuckDuckGoSearchRun()
            raw_text = run_tool.invoke(clean_q)
            if raw_text and isinstance(raw_text, str) and len(raw_text.strip()) > 20:
                results.append({
                    "title": f"Web Search: {clean_q}",
                    "snippet": raw_text.strip(),
                    "url": "https://duckduckgo.com/?q=" + urllib.parse.quote(clean_q),
                    "source": "duckduckgo.com",
                    "date": tf_label if tf_label else ""
                })
        except Exception as e:
            logger.warning(f"[WEB_SEARCH] DuckDuckGoSearchRun fallback encountered: {e}")

    if results:
        logger.info(f"[WEB_SEARCH] Successfully retrieved {len(results)} structured results.")
        return {
            "status": "success",
            "query": clean_q,
            "timeframe": timeframe,
            "timeframe_label": tf_label,
            "results": results[:max_results],
            "provider": "DuckDuckGo",
            "error": None
        }
    else:
        logger.warning(f"[WEB_SEARCH] Zero results retrieved for query: '{clean_q}'.")
        return {
            "status": "error",
            "query": clean_q,
            "timeframe": timeframe,
            "timeframe_label": tf_label,
            "results": [],
            "provider": "DuckDuckGo",
            "error": "Search provider returned no results or timed out."
        }


async def search_web_structured_async(
    query: str, 
    timeframe: Optional[str] = None, 
    max_results: int = 5, 
    timeout: float = 6.0
) -> Dict[str, Any]:
    """Asynchronous wrapper for search_web_structured with non-blocking timeout handling."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(search_web_structured, query, timeframe, max_results),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"[WEB_SEARCH] Search timed out after {timeout}s for query: '{query}'")
        return {
            "status": "error",
            "query": query,
            "timeframe": timeframe,
            "timeframe_label": get_timeframe_label(timeframe),
            "results": [],
            "provider": "DuckDuckGo",
            "error": f"Search provider timed out after {timeout}s."
        }
    except Exception as exc:
        logger.error(f"[WEB_SEARCH] Async search failed: {exc}")
        return {
            "status": "error",
            "query": query,
            "timeframe": timeframe,
            "timeframe_label": get_timeframe_label(timeframe),
            "results": [],
            "provider": "DuckDuckGo",
            "error": str(exc)
        }


def format_web_search_context(search_data: Dict[str, Any]) -> str:
    """Formats structured search results into a clean markdown context block for LLM prompt grounding."""
    results = search_data.get("results", [])
    if not results:
        return "No web search results available."

    query = search_data.get("query", "")
    tf_label = search_data.get("timeframe_label", "")
    header = f"### Live Web Search Results for \"{query}\""
    if tf_label:
        header += f" ({tf_label})"

    blocks = [header, "The following verified sources and summaries were retrieved from the live web:\n"]
    for idx, r in enumerate(results, start=1):
        t = r.get("title") or "Article"
        src = r.get("source") or "Web Source"
        url = r.get("url") or ""
        date_str = r.get("date") or ""
        snip = r.get("snippet") or ""

        meta_line = f"- **Source**: [{src}]({url})" if url else f"- **Source**: {src}"
        if date_str:
            meta_line += f" • **Date / Timeframe**: {date_str}"

        blocks.append(f"{idx}. **{t}**\n   {meta_line}\n   - **Summary**: {snip}\n")

    blocks.append("CRITICAL: Base your response directly on the headlines and summaries above. Cite sources with their publishers or links.")
    return "\n".join(blocks)


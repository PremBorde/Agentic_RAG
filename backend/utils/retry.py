import asyncio
import time
import random
import logging
from typing import Any, Callable, AsyncGenerator

from googleapiclient.errors import HttpError

logger = logging.getLogger("agentic_studio.retry")

# Retryable Google API HTTP status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def execute_with_backoff(request: Any, max_retries: int = 3, initial_delay: float = 1.0, factor: float = 2.0) -> Any:
    """
    Executes a Google API client request with exponential backoff on transient errors.
    Catches 429 (Rate Limit) and 5xx (Server Errors), retrying up to max_retries.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return request.execute()
        except HttpError as e:
            last_exception = e
            status = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else None
            if status in RETRYABLE_STATUS_CODES and attempt < max_retries:
                # Add jitter to avoid thundering herd
                jitter = random.uniform(0.1, 0.4)
                sleep_time = (delay * (factor ** (attempt - 1))) + jitter
                logger.warning(f"Google API transient error HTTP {status} (attempt {attempt}/{max_retries}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            else:
                raise e
        except (ConnectionError, TimeoutError, OSError) as e:
            last_exception = e
            if attempt < max_retries:
                jitter = random.uniform(0.1, 0.4)
                sleep_time = (delay * (factor ** (attempt - 1))) + jitter
                logger.warning(f"Google API network error {e} (attempt {attempt}/{max_retries}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            else:
                raise e

    if last_exception:
        raise last_exception

def is_retryable_llm_error(exc: Exception) -> bool:
    """Checks if an LLM exception is a rate-limit (429) or transient backend error."""
    msg = str(exc).lower()
    return any(k in msg for k in ["429", "resource_exhausted", "resourceexhausted", "quota", "overloaded", "503", "500"])

async def astream_with_backoff(
    llm: Any,
    prompt_val: Any,
    max_retries: int = 3,
    initial_delay: float = 1.5,
    factor: float = 2.0
) -> AsyncGenerator[Any, None]:
    """
    Streams chunks from an LLM with exponential backoff retries if rate-limited (429 / RESOURCE_EXHAUSTED).
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            async for chunk in llm.astream(prompt_val):
                yield chunk
            return
        except Exception as exc:
            if is_retryable_llm_error(exc) and attempt < max_retries:
                jitter = random.uniform(0.2, 0.6)
                sleep_time = (delay * (factor ** (attempt - 1))) + jitter
                logger.warning(f"Gemini LLM stream rate limit/transient error (attempt {attempt}/{max_retries}). Retrying in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
            else:
                raise exc

def format_friendly_error(exc: Exception) -> str:
    """
    Converts raw exceptions into clear, friendly, and actionable UI messages.
    Guarantees no internal stack traces or raw technical details are exposed to users.
    """
    if isinstance(exc, HttpError):
        status = exc.resp.status if hasattr(exc, 'resp') and hasattr(exc.resp, 'status') else 0
        if status == 429:
            return (
                "⏳ **Google API Rate Limit**\n\n"
                "Google Workspace services are temporarily receiving high request volume. "
                "Please wait a few moments before trying again."
            )
        elif status == 401:
            return (
                "🔒 **Google Workspace Authorization Expired**\n\n"
                "Your Google session token has expired or been revoked. "
                "Please reconnect your Google account using the **Connect Google** button above."
            )
        elif status == 403:
            return (
                "🚫 **Permission Denied**\n\n"
                "Google Workspace permissions have not been granted for this operation. "
                "Please verify your Google OAuth consent scopes or reconnect your account."
            )
        elif status == 404:
            return (
                "🔍 **Resource Not Found**\n\n"
                "The requested email message or calendar event could not be located in your Google account."
            )
        elif status in (500, 502, 503, 504):
            return (
                "⚠️ **Google Service Unavailable**\n\n"
                "Google Workspace servers encountered a temporary issue. Please retry in a few moments."
            )

    err_str = str(exc)
    err_lower = err_str.lower()

    if any(k in err_lower for k in ["429", "resource_exhausted", "resourceexhausted", "quota"]):
        return (
            "⚠️ **Gemini API Rate Limit Reached**\n\n"
            "The Google Gemini model is temporarily busy (Free Tier quota reached). "
            "Please select a different model in the dropdown above (e.g., Gemini 3.5 Flash Lite or Gemini 3.8 Flash) "
            "or wait a few moments before sending your next request."
        )

    if any(k in err_lower for k in ["timeout", "timed out", "connection error", "connectionerror", "socket"]):
        return (
            "🌐 **Network Connection Timeout**\n\n"
            "Unable to reach the remote AI or Google services. Please verify your internet connection and try again."
        )

    if "invalid credentials" in err_lower or "token" in err_lower and "expired" in err_lower:
        return (
            "🔒 **Authentication Expired**\n\n"
            "Your login credentials or API keys need re-authentication. Please check your connection settings."
        )

    # General fallback - sanitized, friendly, no stack traces
    return (
        "⚠️ **Unable to Complete Request**\n\n"
        "We encountered an unexpected issue while processing your request. "
        "Please try rephrasing your question or selecting another model."
    )


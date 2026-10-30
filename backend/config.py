import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional

load_dotenv()

# Multi-Model Cache for dynamic Gemini model selection
_llm_cache = {}

AVAILABLE_MODELS = [
    {"id": "gemini-3.5-flash-lite", "label": "Gemini 3.5 Flash Lite (Recommended)"},
    {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash"},
    {"id": "gemini-flash-latest", "label": "Gemini Flash (Latest)"}
]

DEFAULT_MODEL = "gemini-3.5-flash-lite"

def get_llm(model_name: Optional[str] = None):
    """Returns a cached LangChain LLM instance for the specified Gemini model."""
    # Map deprecated, 404, or zero-quota models directly to the active, supported Google model
    deprecated_or_unsupported = {
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-3.1-pro-preview",
        "gemini-3.8-flash"
    }
    if not model_name or model_name in deprecated_or_unsupported:
        model_name = DEFAULT_MODEL

    if model_name not in _llm_cache:
        _llm_cache[model_name] = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.2,
            max_retries=2
        )
    return _llm_cache[model_name]

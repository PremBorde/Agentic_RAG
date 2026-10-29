import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional

load_dotenv()

# Multi-Model Cache for dynamic Gemini model selection
_llm_cache = {}

AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Fast)"},
    {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash Lite (Fastest)"},
    {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash"},
    {"id": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro"}
]

def get_llm(model_name: Optional[str] = None):
    """Returns a cached LangChain LLM instance for the specified Gemini model."""
    if not model_name or model_name in ("gemini-3.5-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash"):
        model_name = "gemini-2.5-flash"
    if model_name not in _llm_cache:
        _llm_cache[model_name] = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.2,
            max_retries=2
        )
    return _llm_cache[model_name]

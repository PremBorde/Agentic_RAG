import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional

load_dotenv()

# Ensure GOOGLE_API_KEY uses the authentic Gemini API key if set as GEMINI_API_KEY
if os.getenv("GEMINI_API_KEY") and not (os.getenv("GOOGLE_API_KEY", "").startswith("AIzaSy")):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# Multi-Model Cache for dynamic Gemini model selection
_llm_cache = {}

AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Ultra Fast & Recommended)"},
    {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash Lite (Lowest Latency)"},
    {"id": "gemini-3.5-flash-lite", "label": "Gemini 3.5 Flash Lite (Deep Reasoning)"}
]

DEFAULT_MODEL = "gemini-2.5-flash"

def get_llm(model_name: Optional[str] = None):
    """Returns a cached LangChain LLM instance for the specified Gemini model."""
    # Map deprecated, 404, or legacy models to high-speed stable models
    alias_map = {
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-2.0-flash": "gemini-2.5-flash",
        "gemini-3-flash-preview": "gemini-2.5-flash",
        "gemini-flash-latest": "gemini-2.5-flash"
    }
    if model_name in alias_map:
        model_name = alias_map[model_name]
    elif not model_name:
        model_name = DEFAULT_MODEL

    if model_name not in _llm_cache:
        _llm_cache[model_name] = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.2,
            max_retries=1
        )
    return _llm_cache[model_name]

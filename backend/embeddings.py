from typing import List
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import TextEmbedding

def safe_str(val) -> str:
    """Safely normalizes any content, list of chunks, or dict structure into a clean string."""
    if isinstance(val, str):
        return val
    elif isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "") or item.get("content", "") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    elif isinstance(val, dict):
        return str(val.get("text", "") or val.get("content", "") or str(val))
    elif val is None:
        return ""
    return str(val)

class LocalFastEmbeddings(Embeddings):
    """Local, ultra-fast embedding model (BGE-small) running locally via ONNX with ZERO API quota limits."""
    def __init__(self, model_name="BAAI/bge-small-en-v1.5"):
        self.model = TextEmbedding(model_name=model_name)
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # FastEmbed batch embedding with batch_size=64 for parallel CPU throughput
        safe_texts = [safe_str(t) for t in texts]
        return [e.tolist() for e in self.model.embed(safe_texts, batch_size=64)]
        
    def embed_query(self, text: str) -> List[float]:
        return list(self.model.embed([safe_str(text)]))[0].tolist()

embeddings = LocalFastEmbeddings()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=750,
    chunk_overlap=90,
    separators=["\n\n", "\n", ". ", " ", ""]
)


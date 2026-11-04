"""
Advanced Chunking Engine with Sentence-Boundary Preservation & Structural Context
Ensures:
- Sentences are never split mid-phrase.
- Headings are preserved and prepended to chunk content for high semantic match.
- Rich chunk-level metadata: doc_id, chunk_id, page_number, heading, source, content_hash.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional

def split_into_sentences(text: str) -> List[str]:
    """Splits a block of text into distinct sentences preserving punctuation."""
    if not text:
        return []
    # Match sentence boundaries (. ! ?) followed by whitespace or linebreaks
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences

def chunk_document_sections(
    sections: List[Dict[str, Any]],
    document_id: str,
    document_name: str,
    document_type: str = "pdf",
    content_hash: str = "",
    chunk_size: int = 500,
    chunk_overlap: int = 75
) -> List[Dict[str, Any]]:
    """
    Transforms structured document sections into heading-aware, sentence-aligned chunks.
    Returns: List[Dict] with 'text' and 'metadata'.
    """
    all_chunks = []
    chunk_counter = 1

    for sec in sections:
        sec_text = sec.get("text", "").strip()
        if not sec_text:
            continue
        page_num = sec.get("page_number", 1)
        heading = sec.get("heading") or "General"

        # Split section into natural sentences
        sentences = split_into_sentences(sec_text)
        if not sentences:
            sentences = [sec_text]

        current_sentences = []
        current_len = 0

        for sentence in sentences:
            sent_len = len(sentence)
            
            # If adding this sentence exceeds chunk_size and we already have content
            if current_len + sent_len > chunk_size and current_sentences:
                chunk_body = " ".join(current_sentences).strip()
                # Include section context in chunk text if heading is informative
                prefixed_text = f"[{heading}]\n{chunk_body}" if heading and heading != "General" else chunk_body
                
                chunk_id = f"{document_id}-c{chunk_counter}"
                chunk_hash = hashlib.sha256(prefixed_text.encode("utf-8")).hexdigest()

                all_chunks.append({
                    "text": prefixed_text,
                    "metadata": {
                        "doc_id": document_id,
                        "chunk_id": chunk_id,
                        "document_name": document_name,
                        "document_type": document_type,
                        "page_number": page_num,
                        "section_heading": heading,
                        "source": document_name,
                        "source_location": f"Page {page_num}" if page_num else (heading or "Document"),
                        "content_hash": chunk_hash
                    }
                })
                chunk_counter += 1

                # Calculate overlap sentences
                overlap_buffer = []
                overlap_len = 0
                for prev_s in reversed(current_sentences):
                    if overlap_len + len(prev_s) <= chunk_overlap:
                        overlap_buffer.insert(0, prev_s)
                        overlap_len += len(prev_s)
                    else:
                        break
                current_sentences = overlap_buffer
                current_len = overlap_len

            current_sentences.append(sentence)
            current_len += sent_len

        # Remaining sentences in section
        if current_sentences:
            chunk_body = " ".join(current_sentences).strip()
            prefixed_text = f"[{heading}]\n{chunk_body}" if heading and heading != "General" else chunk_body
            chunk_id = f"{document_id}-c{chunk_counter}"
            chunk_hash = hashlib.sha256(prefixed_text.encode("utf-8")).hexdigest()

            all_chunks.append({
                "text": prefixed_text,
                "metadata": {
                    "doc_id": document_id,
                    "chunk_id": chunk_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "page_number": page_num,
                    "section_heading": heading,
                    "source": document_name,
                    "source_location": f"Page {page_num}" if page_num else (heading or "Document"),
                    "content_hash": chunk_hash
                }
            })
            chunk_counter += 1

    return all_chunks


"""
Document Ingestion & Parsing Engine
Provides structured, format-specific text extraction for:
- PDF (page-aware, cleans formatting artifacts & bullets)
- DOCX (native XML/docx paragraph, heading, and table extraction)
- CSV (column-aware structured record serialization)
- JSON (structured hierarchical key-value formatting)
- TXT / Markdown (heading-aware and whitespace-normalized)
- YouTube transcripts
"""

import io
import re
import csv
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("parsers")

def clean_text_artifacts(text: str) -> str:
    """Removes non-printable control characters, extraneous bullet encodings, and collapses whitespace."""
    if not text:
        return ""
    # Normalize unicode bullets and special symbols commonly found in academic PDFs
    cleaned = text.replace("\uf0b7", "- ").replace("\u2022", "- ").replace("\xa0", " ")
    # Replace non-printable ASCII (except newline and tab)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
    # Collapse 3+ consecutive newlines to 2
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Collapse multiple spaces and trailing whitespace per line
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.splitlines()]
    return "\n".join(lines).strip()

def parse_pdf(bytes_data: bytes) -> List[Dict[str, Any]]:
    """
    Page-aware PDF extraction.
    Returns list of page dicts: [{'page_number': int, 'text': str, 'heading': Optional[str]}]
    Detects scanned/image-only PDFs and raises an informative error.
    """
    import pypdf
    pages = []
    has_images_only = False
    try:
        reader = pypdf.PdfReader(io.BytesIO(bytes_data))
        total_pages = len(reader.pages)
        for page_idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            cleaned = clean_text_artifacts(raw_text)
            if cleaned:
                # Attempt to extract first prominent heading if present
                first_line = cleaned.splitlines()[0] if cleaned.splitlines() else ""
                heading = first_line[:80] if len(first_line) < 100 else None
                pages.append({
                    "page_number": page_idx,
                    "text": cleaned,
                    "heading": heading
                })
            else:
                try:
                    if hasattr(page, 'images') and len(page.images) > 0:
                        has_images_only = True
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error parsing PDF bytes: {e}")
        raise ValueError(f"Failed to parse PDF document: {str(e)}")

    if not pages and has_images_only:
        raise ValueError(f"Scanned image-only PDF detected ({total_pages} page(s)). This document contains embedded images but no extractable digital text layer. OCR pre-processing is required.")

    return pages

def parse_docx(bytes_data: bytes) -> List[Dict[str, Any]]:
    """
    Parses Microsoft Word (.docx) files preserving headings and tables.
    """
    try:
        import docx
        doc = docx.Document(io.BytesIO(bytes_data))
        sections = []
        current_heading = "General"
        current_buffer = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style and p.style.name.startswith("Heading"):
                if current_buffer:
                    sections.append({
                        "heading": current_heading,
                        "text": clean_text_artifacts("\n".join(current_buffer)),
                        "page_number": 1
                    })
                    current_buffer = []
                current_heading = text
            else:
                current_buffer.append(text)

        # Also extract table text
        for t_idx, table in enumerate(doc.tables, start=1):
            table_rows = []
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    table_rows.append(" | ".join(cells))
            if table_rows:
                current_buffer.append(f"\n[Table {t_idx}]:\n" + "\n".join(table_rows))

        if current_buffer:
            sections.append({
                "heading": current_heading,
                "text": clean_text_artifacts("\n".join(current_buffer)),
                "page_number": 1
            })
        return sections
    except Exception as e:
        logger.error(f"Error parsing DOCX bytes: {e}")
        raise ValueError(f"Failed to parse DOCX document: {str(e)}")

def parse_csv(bytes_data: bytes) -> List[Dict[str, Any]]:
    """
    Parses CSV files into column-header-aware text blocks.
    Groups rows in batches of 5-10 so context is retained.
    """
    try:
        text = bytes_data.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return []
        
        headers = rows[0]
        records = []
        batch = []
        batch_size = 5
        
        for idx, row in enumerate(rows[1:], start=1):
            row_items = []
            for col_idx, val in enumerate(row):
                header = headers[col_idx] if col_idx < len(headers) else f"Col{col_idx+1}"
                row_items.append(f"{header}: {val.strip()}")
            batch.append(f"Row {idx} -> " + ", ".join(row_items))
            
            if len(batch) >= batch_size:
                records.append({
                    "heading": f"Rows {idx-batch_size+1}-{idx}",
                    "text": "\n".join(batch),
                    "page_number": 1
                })
                batch = []
                
        if batch:
            records.append({
                "heading": f"Rows {len(rows)-len(batch)}-{len(rows)-1}",
                "text": "\n".join(batch),
                "page_number": 1
            })
        return records
    except Exception as e:
        logger.error(f"Error parsing CSV bytes: {e}")
        raise ValueError(f"Failed to parse CSV document: {str(e)}")

def parse_json(bytes_data: bytes) -> List[Dict[str, Any]]:
    """
    Parses structured JSON documents into key-aware document blocks.
    """
    try:
        raw_str = bytes_data.decode("utf-8", errors="ignore")
        data = json.loads(raw_str)
        sections = []
        
        if isinstance(data, list):
            batch = []
            for idx, item in enumerate(data, start=1):
                item_str = json.dumps(item, indent=2, ensure_ascii=False)
                batch.append(f"[Item {idx}]:\n{item_str}")
                if len(batch) >= 5:
                    sections.append({
                        "heading": f"Items {idx-4}-{idx}",
                        "text": "\n\n".join(batch),
                        "page_number": 1
                    })
                    batch = []
            if batch:
                sections.append({
                    "heading": f"Remaining Items",
                    "text": "\n\n".join(batch),
                    "page_number": 1
                })
        elif isinstance(data, dict):
            for key, val in data.items():
                val_str = json.dumps(val, indent=2, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
                sections.append({
                    "heading": str(key),
                    "text": f"### {key}\n{val_str}",
                    "page_number": 1
                })
        return sections
    except Exception as e:
        logger.error(f"Error parsing JSON bytes: {e}")
        raise ValueError(f"Failed to parse JSON document: {str(e)}")

def parse_plain_or_markdown(bytes_data: bytes) -> List[Dict[str, Any]]:
    """
    Parses TXT or Markdown files with heading awareness.
    """
    text = clean_text_artifacts(bytes_data.decode("utf-8", errors="ignore"))
    sections = []
    current_heading = "General"
    current_buffer = []

    for line in text.splitlines():
        if re.match(r'^#{1,3}\s+', line):
            if current_buffer:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_buffer).strip(),
                    "page_number": 1
                })
                current_buffer = []
            current_heading = re.sub(r'^#{1,3}\s+', '', line).strip()
        else:
            current_buffer.append(line)

    if current_buffer:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_buffer).strip(),
            "page_number": 1
        })
    return sections if sections else [{"heading": "General", "text": text, "page_number": 1}]


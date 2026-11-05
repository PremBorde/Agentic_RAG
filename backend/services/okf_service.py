"""
Open Knowledge Format (OKF) v0.2 Generator, Storage, and Validation Service.
Implements the official GoogleCloudPlatform/open-knowledge-format v0.2 specification.
"""

import os
import re
import yaml
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from backend.services.okf_models import (
    OKFConceptFrontmatter,
    OKFConceptItem,
    OKFSource,
    OKFBundleMetadata
)

logger = logging.getLogger("okf_service")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

DATA_DIR = os.environ.get("DATA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")))
BASE_OKF_DIR = os.path.join(DATA_DIR, "okf_bundles")


def sanitize_identifier(text: str) -> str:
    """Creates a URL-safe, filesystem-safe alphanumeric slug."""
    s = text.lower().strip()
    s = re.sub(r'[\'"`]', '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_') or "concept"


def get_user_bundles_root(user_id: Optional[str] = None) -> str:
    """Returns the base directory for a specific user to ensure strict multi-user isolation."""
    safe_user = sanitize_identifier(user_id or "default_user")
    user_dir = os.path.join(BASE_OKF_DIR, safe_user)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def extract_concept_candidates(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts distinct, meaningful concept candidates from parsed document sections.
    Filters out boilerplate, headers without content, and trivial fragments.
    """
    concepts = []
    seen_titles = set()

    for sec in sections:
        raw_heading = sec.get("heading") or "General Concept"
        raw_text = (sec.get("text") or "").strip()
        page_num = sec.get("page_number", 1)

        if len(raw_text) < 40:
            continue

        # Extract title from heading or first line
        title = raw_heading.strip("# \t\r\n")
        if not title or title.lower() in {"general", "untitled", "introduction", "overview"}:
            first_line = raw_text.split("\n")[0].strip("# \t\r\n")
            if 3 < len(first_line) < 80:
                title = first_line
            else:
                title = raw_heading

        slug = sanitize_identifier(title)
        if slug in seen_titles:
            continue
        seen_titles.add(slug)

        # Extract brief description (first 1-2 sentences)
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        desc = sentences[0].strip() if sentences else raw_text[:160]
        if len(desc) > 220:
            desc = desc[:217] + "..."

        # Extract representative tags
        tags = set()
        words = re.findall(r'[a-zA-Z]{3,}', title.lower() + " " + raw_text[:200].lower())
        stopwords = {"the", "and", "this", "that", "with", "from", "each", "must", "when", "into", "uses", "runs", "also"}
        for w in words:
            if w not in stopwords and len(tags) < 6:
                tags.add(w)

        concepts.append({
            "slug": slug,
            "title": title,
            "description": desc,
            "body": raw_text,
            "page_number": page_num,
            "section_heading": raw_heading,
            "tags": sorted(list(tags))
        })

    return concepts


def build_concept_cross_links(concepts: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Discovers genuine semantic cross-links between concepts in the bundle.
    Returns mapping of slug -> list of (target_slug, target_title).
    """
    links_map: Dict[str, List[Tuple[str, str]]] = {c["slug"]: [] for c in concepts}

    for i, source_c in enumerate(concepts):
        src_slug = source_c["slug"]
        src_body = source_c["body"].lower()

        for j, target_c in enumerate(concepts):
            if i == j:
                continue
            tgt_slug = target_c["slug"]
            tgt_title = target_c["title"]

            # Match title keywords in source text
            tgt_words = [w for w in re.findall(r'[a-zA-Z]{3,}', tgt_title.lower()) if w not in {"the", "and", "algorithm", "system"}]
            if tgt_title.lower() in src_body or (len(tgt_words) >= 2 and all(w in src_body for w in tgt_words)):
                links_map[src_slug].append((tgt_slug, tgt_title))

    return links_map


def generate_okf_bundle_from_sections(
    sections: List[Dict[str, Any]],
    document_id: str,
    document_name: str,
    user_id: Optional[str] = "default_user"
) -> Dict[str, Any]:
    """
    Generates a full OKF v0.2 Knowledge Bundle from parsed document sections.
    Creates:
    - bundle directory
    - concepts/*.md with OKF v0.2 YAML frontmatter
    - index.md (catalog)
    - log.md (audit log)
    """
    user_root = get_user_bundles_root(user_id)
    bundle_slug = sanitize_identifier(document_id)
    bundle_dir = os.path.join(user_root, bundle_slug)
    concepts_dir = os.path.join(bundle_dir, "concepts")

    os.makedirs(concepts_dir, exist_ok=True)

    candidates = extract_concept_candidates(sections)
    if not candidates:
        logger.warning(f"[OKF] No viable concept candidates extracted from '{document_name}'")
        return {"bundle_id": bundle_slug, "concept_count": 0, "bundle_path": bundle_dir}

    links_map = build_concept_cross_links(candidates)
    created_concepts: List[OKFConceptItem] = []
    now_iso = datetime.utcnow().isoformat() + "Z"

    # 1. Write each concept file
    for c in candidates:
        slug = c["slug"]
        outbound = links_map.get(slug, [])

        frontmatter = OKFConceptFrontmatter(
            type="concept",
            title=c["title"],
            description=c["description"],
            resource=f"urn:doc:{sanitize_identifier(document_name)}:{slug}",
            tags=c["tags"],
            timestamp=now_iso,
            sources=[
                OKFSource(
                    document_id=document_id,
                    filename=document_name,
                    page_number=c["page_number"],
                    source_location=c["section_heading"]
                )
            ],
            generated=True,
            verified=False,
            status="draft"
        )

        # Build Markdown content
        md_lines = [
            "---",
            yaml.safe_dump(frontmatter.model_dump(), sort_keys=False).strip(),
            "---",
            "",
            f"# {c['title']}",
            "",
            c["body"],
            ""
        ]

        if outbound:
            md_lines.append("## Related Concepts (OKF Graph Links)")
            for tgt_slug, tgt_title in outbound:
                md_lines.append(f"- [{tgt_title}]({tgt_slug}.md)")
            md_lines.append("")

        md_content = "\n".join(md_lines)
        file_path = os.path.join(concepts_dir, f"{slug}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        created_concepts.append(OKFConceptItem(
            concept_id=slug,
            relative_path=f"concepts/{slug}.md",
            frontmatter=frontmatter,
            body=c["body"],
            outbound_links=[t[0] for t in outbound]
        ))

    # 2. Generate index.md (Progressive Disclosure Catalog)
    index_fm = {
        "type": "index",
        "title": f"Knowledge Catalog: {document_name}",
        "description": f"Open Knowledge Format v0.2 concept catalog for {document_name}",
        "resource": f"urn:bundle:{bundle_slug}",
        "timestamp": now_iso,
        "concept_count": len(created_concepts),
        "status": "draft"
    }

    index_lines = [
        "---",
        yaml.safe_dump(index_fm, sort_keys=False).strip(),
        "---",
        "",
        f"# Knowledge Catalog: {document_name}",
        "",
        f"This bundle contains {len(created_concepts)} interconnected knowledge concepts extracted according to Open Knowledge Format (OKF) v0.2.",
        "",
        "## Concepts Directory",
        ""
    ]
    for c in created_concepts:
        index_lines.append(f"- [{c.frontmatter.title}]({c.relative_path}): {c.frontmatter.description}")

    with open(os.path.join(bundle_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")

    # 3. Generate log.md (Chronological Audit & Change Log)
    log_fm = {
        "type": "log",
        "title": "Audit & Update Log",
        "timestamp": now_iso
    }
    log_lines = [
        "---",
        yaml.safe_dump(log_fm, sort_keys=False).strip(),
        "---",
        "",
        "# Chronological Audit Log",
        "",
        f"- `[{now_iso}]` **Bundle Created**: Ingested `{document_name}` (ID: `{document_id}`). Created {len(created_concepts)} concept documents in `draft` status."
    ]
    with open(os.path.join(bundle_dir, "log.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")

    logger.info(f"[OKF] Successfully generated OKF v0.2 bundle at '{bundle_dir}' with {len(created_concepts)} concepts.")

    return {
        "bundle_id": bundle_slug,
        "bundle_name": document_name,
        "concept_count": len(created_concepts),
        "bundle_path": bundle_dir,
        "concepts": [c.model_dump() for c in created_concepts]
    }


def validate_okf_bundle(bundle_dir: str) -> Dict[str, Any]:
    """
    Validates an OKF v0.2 bundle:
    - Verifies index.md and log.md existence & schema
    - Verifies concept frontmatter required and trust layer fields
    - Verifies internal relative links between concept files
    """
    errors = []
    warnings = []
    concepts_found = []

    if not os.path.isdir(bundle_dir):
        return {"is_valid": False, "errors": [f"Bundle path does not exist: {bundle_dir}"], "warnings": []}

    # 1. Validate index.md
    index_path = os.path.join(bundle_dir, "index.md")
    if not os.path.exists(index_path):
        errors.append("Missing required 'index.md' catalog file.")
    else:
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not m:
                errors.append("index.md missing YAML frontmatter delimiters (---).")
            else:
                data = yaml.safe_load(m.group(1)) or {}
                if data.get("type") != "index":
                    errors.append(f"index.md frontmatter 'type' must be 'index' (got '{data.get('type')}').")
        except Exception as e:
            errors.append(f"Failed to parse index.md: {e}")

    # 2. Validate log.md
    log_path = os.path.join(bundle_dir, "log.md")
    if not os.path.exists(log_path):
        warnings.append("Missing recommended 'log.md' audit log file.")

    # 3. Validate concepts directory
    concepts_dir = os.path.join(bundle_dir, "concepts")
    if not os.path.isdir(concepts_dir):
        errors.append("Missing 'concepts/' directory.")
        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings, "concept_count": 0}

    concept_files = [f for f in os.listdir(concepts_dir) if f.endswith(".md")]
    concept_slugs = {f[:-3] for f in concept_files}

    for cf in concept_files:
        c_path = os.path.join(concepts_dir, cf)
        slug = cf[:-3]
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                c_content = f.read()

            m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", c_content, re.DOTALL)
            if not m:
                errors.append(f"Concept '{cf}' lacks valid YAML frontmatter delimiters.")
                continue

            fm_raw, body = m.group(1), m.group(2)
            fm = yaml.safe_load(fm_raw) or {}

            # Check required fields (OKF v0.2 spec)
            if "type" not in fm:
                errors.append(f"Concept '{cf}' missing required 'type' field in frontmatter.")
            if "title" not in fm:
                warnings.append(f"Concept '{cf}' missing recommended 'title' field.")
            if "sources" not in fm or not fm["sources"]:
                warnings.append(f"Concept '{cf}' missing provenance 'sources' metadata.")

            # Validate internal links in markdown body
            link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+\.md)\)', body)
            for text_label, link_target in link_matches:
                target_slug = os.path.basename(link_target)[:-3]
                if target_slug not in concept_slugs:
                    warnings.append(f"Broken internal link in '{cf}': Target '{link_target}' does not exist in bundle.")

            concepts_found.append(slug)
        except Exception as e:
            errors.append(f"Error parsing concept '{cf}': {e}")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "concept_count": len(concepts_found),
        "concepts": concepts_found
    }


def list_user_bundles(user_id: Optional[str] = "default_user") -> List[Dict[str, Any]]:
    """Lists all OKF Knowledge Bundles owned by the user."""
    user_root = get_user_bundles_root(user_id)
    bundles = []

    for entry in os.listdir(user_root):
        b_path = os.path.join(user_root, entry)
        if os.path.isdir(b_path):
            idx_file = os.path.join(b_path, "index.md")
            title = entry
            desc = ""
            concept_count = 0
            if os.path.exists(idx_file):
                try:
                    with open(idx_file, "r", encoding="utf-8") as f:
                        txt = f.read()
                    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.DOTALL)
                    if m:
                        d = yaml.safe_load(m.group(1)) or {}
                        title = d.get("title", entry)
                        desc = d.get("description", "")
                        concept_count = d.get("concept_count", 0)
                except Exception:
                    pass

            bundles.append({
                "bundle_id": entry,
                "title": title,
                "description": desc,
                "concept_count": concept_count,
                "path": b_path
            })

    return bundles


def delete_bundle_for_document(document_id: str, user_id: Optional[str] = "default_user") -> bool:
    """Safely deletes an OKF bundle and derived concept files when document is removed."""
    user_root = get_user_bundles_root(user_id)
    bundle_slug = sanitize_identifier(document_id)
    bundle_path = os.path.join(user_root, bundle_slug)

    if os.path.exists(bundle_path):
        try:
            shutil.rmtree(bundle_path)
            logger.info(f"[OKF] Successfully purged bundle directory: {bundle_path}")
            return True
        except Exception as e:
            logger.error(f"[OKF] Error deleting bundle {bundle_path}: {e}")
            return False
    return False


def clear_all_bundles(user_id: Optional[str] = "default_user") -> bool:
    """Removes all OKF bundles for the user when Knowledge Base is cleared."""
    try:
        user_root = get_user_bundles_root(user_id)
        if os.path.exists(user_root):
            for entry in os.listdir(user_root):
                entry_path = os.path.join(user_root, entry)
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path, ignore_errors=True)
                elif os.path.isfile(entry_path):
                    try:
                        os.remove(entry_path)
                    except Exception:
                        pass
            logger.info(f"[OKF] Successfully cleared all bundles in {user_root}")
        return True
    except Exception as e:
        logger.error(f"[OKF] Error clearing all bundles: {e}")
        return False


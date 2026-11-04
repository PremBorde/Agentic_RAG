"""
Open Knowledge Format (OKF) v0.2 Knowledge Retriever & Graph Traversal Engine.
Discovers relevant concepts and traverses outbound markdown links for multi-hop synthesis.
"""

import os
import re
import yaml
import logging
from typing import List, Dict, Any, Optional, Set

from backend.services.okf_service import get_user_bundles_root

logger = logging.getLogger("okf_retriever")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def is_relational_or_multihop_query(query: str) -> bool:
    """
    Determines whether a query benefits from OKF concept graph retrieval.
    Detects comparisons, multi-hop questions, relationship inquiries, and conceptual definitions.
    Prevents invoking OKF for simple one-off keyword lookups.
    """
    t = query.lower().strip()

    triggers = [
        "compare", "comparison", "difference between", "differences between", "differ from",
        "versus", " vs ", " vs. ", "relationship between", "relation between", "how does .* relate to",
        "how do .* and .* connect", "connection between", "how are .* related", "connect",
        "contrast", "contrasting", "trade-off", "trade off", "tradeoff", "better than",
        "advantages of .* over", "disadvantages of", "pros and cons", "why would you use .* instead of",
        "prerequisite", "prerequisites", "dependency", "dependencies", "lifecycle", "pipeline",
        "architecture", "hierarchy", "cause and effect", "how does .* affect", "impact of .* on",
        "explain the concepts", "conceptually", "underlying principles", "multi-hop", "cross-reference",
        "synthesize", "synthesizing", "how do these relate", "relate to each other"
    ]

    for trig in triggers:
        if re.search(rf"\b{trig}\b", t) or (trig in t):
            return True

    # Check if query mentions multiple distinct capitalized entities or technical terms
    words = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+\b', query)
    if len(words) >= 2 and any(k in t for k in ["and", "or", "with", "both"]):
        return True

    return False


def parse_concept_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Reads and parses an OKF concept file into a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not m:
            return None

        fm_raw, body = m.group(1), m.group(2).strip()
        fm = yaml.safe_load(fm_raw) or {}

        # Extract outbound markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+\.md)\)', body)
        outbound = [{"title": l[0], "target_slug": os.path.basename(l[1])[:-3]} for l in links]

        return {
            "slug": os.path.basename(file_path)[:-3],
            "file_path": file_path,
            "title": fm.get("title", os.path.basename(file_path)[:-3]),
            "description": fm.get("description", ""),
            "tags": fm.get("tags", []),
            "sources": fm.get("sources", []),
            "status": fm.get("status", "draft"),
            "verified": fm.get("verified", False),
            "generated": fm.get("generated", True),
            "body": body,
            "outbound_links": outbound
        }
    except Exception as e:
        logger.warning(f"[OKF_RETRIEVER] Failed to parse concept file '{file_path}': {e}")
        return None


def retrieve_okf_concepts(
    query: str,
    user_id: Optional[str] = "default_user",
    max_concepts: int = 3,
    max_depth: int = 1
) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant OKF concepts for a query and traverses graph links up to max_depth.
    Strictly isolates bundles by user_id to prevent cross-user knowledge leakage.
    """
    user_root = get_user_bundles_root(user_id)
    if not os.path.isdir(user_root):
        return []

    # Gather all available concept files for the user
    all_concepts: Dict[str, Dict[str, Any]] = {}
    for bundle_entry in os.listdir(user_root):
        c_dir = os.path.join(user_root, bundle_entry, "concepts")
        if os.path.isdir(c_dir):
            for cf in os.listdir(c_dir):
                if cf.endswith(".md"):
                    full_p = os.path.join(c_dir, cf)
                    parsed = parse_concept_file(full_p)
                    if parsed:
                        all_concepts[parsed["slug"]] = parsed

    if not all_concepts:
        return []

    # Score each concept against query
    q_lower = query.lower()
    q_words = set(re.findall(r'[a-zA-Z0-9]{3,}', q_lower))
    stopwords = {"what", "how", "why", "does", "explain", "between", "from", "with", "about", "which"}
    meaningful_q_words = q_words - stopwords

    scored: List[Tuple[float, str]] = []

    for slug, c in all_concepts.items():
        score = 0.0
        title_lower = c["title"].lower()

        # Exact title match
        if title_lower in q_lower:
            score += 15.0

        # Title words match
        t_words = set(re.findall(r'[a-zA-Z0-9]{3,}', title_lower))
        score += 4.0 * len(t_words & meaningful_q_words)

        # Tags match
        tag_set = {t.lower() for t in c["tags"]}
        score += 2.5 * len(tag_set & meaningful_q_words)

        # Description match
        desc_words = set(re.findall(r'[a-zA-Z0-9]{3,}', c["description"].lower()))
        score += 1.0 * len(desc_words & meaningful_q_words)

        if score > 0:
            scored.append((score, slug))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return []

    # Select top initial concept seeds
    selected_slugs: Set[str] = set()
    results: List[Dict[str, Any]] = []

    top_seeds = [slug for _, slug in scored[:2]]
    for s in top_seeds:
        selected_slugs.add(s)
        results.append(all_concepts[s])

    # Graph Traversal (Hop 1): Follow outbound links if capacity allows
    if max_depth >= 1 and len(results) < max_concepts:
        for seed_concept in list(results):
            for link in seed_concept.get("outbound_links", []):
                tgt = link.get("target_slug")
                if tgt and tgt in all_concepts and tgt not in selected_slugs:
                    selected_slugs.add(tgt)
                    results.append(all_concepts[tgt])
                    if len(results) >= max_concepts:
                        break
            if len(results) >= max_concepts:
                break

    logger.info(f"[OKF_RETRIEVER] Retrieved {len(results)} concepts for query: '{query[:45]}'")
    return results[:max_concepts]


def format_okf_context(concepts: List[Dict[str, Any]]) -> str:
    """Formats retrieved OKF concepts into structured context for the LLM prompt."""
    if not concepts:
        return ""

    blocks = ["\n=== Open Knowledge Format (OKF) Verified Concept Graph ==="]
    for i, c in enumerate(concepts, start=1):
        src_info = ""
        if c.get("sources"):
            first_src = c["sources"][0]
            src_info = f" (Source: {first_src.get('filename')}, Page {first_src.get('page_number')})"

        related = [l["title"] for l in c.get("outbound_links", [])]
        related_str = f" | Connected Concepts: {', '.join(related)}" if related else ""

        block = [
            f"[OKF Concept {i}] {c['title']} [Status: {c['status']}{src_info}{related_str}]",
            c["body"].strip()
        ]
        blocks.append("\n".join(block))

    return "\n\n".join(blocks)


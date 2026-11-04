"""
FastAPI Routes for Open Knowledge Format (OKF) v0.2 Knowledge Bundles.
Provides endpoints to inspect, retrieve, and validate OKF bundles with multi-user isolation.
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from backend.utils.auth import get_current_user_id
from backend.services.okf_service import (
    list_user_bundles,
    validate_okf_bundle,
    get_user_bundles_root,
    delete_bundle_for_document
)
from backend.services.okf_retriever import (
    retrieve_okf_concepts,
    format_okf_context,
    is_relational_or_multihop_query
)

router = APIRouter(prefix="/api/okf", tags=["okf"])


class ValidateRequest(BaseModel):
    bundle_id: str


class RetrieveRequest(BaseModel):
    query: str
    max_concepts: Optional[int] = 3
    max_depth: Optional[int] = 1


@router.get("/bundles")
def get_user_bundles(request: Request):
    """Lists all OKF v0.2 knowledge bundles owned by the active user."""
    user_id = get_current_user_id(request)
    bundles = list_user_bundles(user_id=user_id)
    return {"bundles": bundles, "count": len(bundles)}


@router.get("/bundles/{bundle_id}")
def get_bundle_details(bundle_id: str, request: Request):
    """Retrieves metadata and validation status for a specific bundle."""
    user_id = get_current_user_id(request)
    user_root = get_user_bundles_root(user_id)
    bundle_path = os.path.join(user_root, bundle_id)

    if not os.path.isdir(bundle_path):
        raise HTTPException(status_code=404, detail=f"OKF Bundle '{bundle_id}' not found.")

    val_result = validate_okf_bundle(bundle_path)

    # Read index.md
    index_content = ""
    idx_file = os.path.join(bundle_path, "index.md")
    if os.path.exists(idx_file):
        with open(idx_file, "r", encoding="utf-8") as f:
            index_content = f.read()

    return {
        "bundle_id": bundle_id,
        "bundle_path": bundle_path,
        "validation": val_result,
        "index_markdown": index_content
    }


@router.post("/validate")
def validate_bundle_endpoint(req: ValidateRequest, request: Request):
    """Validates bundle structure, YAML frontmatter, and internal relative links."""
    user_id = get_current_user_id(request)
    user_root = get_user_bundles_root(user_id)
    bundle_path = os.path.join(user_root, req.bundle_id)

    if not os.path.isdir(bundle_path):
        raise HTTPException(status_code=404, detail=f"OKF Bundle '{req.bundle_id}' not found.")

    return validate_okf_bundle(bundle_path)


@router.post("/retrieve")
def retrieve_concepts_endpoint(req: RetrieveRequest, request: Request):
    """Queries the user's OKF concept graph with outbound link traversal."""
    user_id = get_current_user_id(request)
    is_rel = is_relational_or_multihop_query(req.query)
    concepts = retrieve_okf_concepts(
        query=req.query,
        user_id=user_id,
        max_concepts=req.max_concepts or 3,
        max_depth=req.max_depth or 1
    )
    formatted = format_okf_context(concepts)

    return {
        "query": req.query,
        "is_relational": is_rel,
        "concept_count": len(concepts),
        "concepts": concepts,
        "formatted_context": formatted
    }


"""
Open Knowledge Format (OKF) v0.2 Data Models and Schema Definitions.
Conforms to GoogleCloudPlatform/open-knowledge-format v0.2 specification.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OKFSource(BaseModel):
    """Provenance tracking for a source document or chunk in OKF v0.2."""
    document_id: str
    filename: str
    page_number: Optional[int] = 1
    source_location: Optional[str] = None
    content_hash: Optional[str] = None


class OKFConceptFrontmatter(BaseModel):
    """
    Standard YAML frontmatter for an OKF v0.2 concept document.
    Required: type
    Recommended: title, description, resource, tags, timestamp
    v0.2 Trust Layer: sources, generated, verified, status, stale_after
    """
    type: Literal["concept", "procedure", "policy", "reference", "topic", "entity", "index", "log"] = "concept"
    title: str
    description: str
    resource: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sources: List[OKFSource] = Field(default_factory=list)
    generated: bool = True
    verified: bool = False
    status: Literal["draft", "active", "deprecated"] = "draft"
    stale_after: Optional[str] = None


class OKFConceptItem(BaseModel):
    """Represents a parsed OKF concept file with frontmatter and body."""
    concept_id: str
    relative_path: str
    frontmatter: OKFConceptFrontmatter
    body: str
    outbound_links: List[str] = Field(default_factory=list)


class OKFBundleMetadata(BaseModel):
    """Metadata describing an entire OKF Knowledge Bundle."""
    bundle_id: str
    bundle_name: str
    user_id: str
    source_document_id: str
    source_filename: str
    created_at: str
    concept_count: int
    bundle_path: str


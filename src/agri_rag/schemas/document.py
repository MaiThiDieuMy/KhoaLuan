from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class DocumentRecord:
    # -------------------------
    # Identity
    # -------------------------
    document_id: str
    source_id: str
    url: str

    # -------------------------
    # Basic document metadata
    # -------------------------
    title: Optional[str] = None
    published_date: Optional[str] = None
    document_family: Optional[str] = None
    content_type: Optional[str] = None

    # -------------------------
    # Agricultural metadata
    # -------------------------
    buckets: List[str] = field(default_factory=list)
    crop_entities: List[str] = field(default_factory=list)

    suggested_buckets: List[str] = field(default_factory=list)

    metadata_status: str = "PENDING"
    metadata_notes: List[str] = field(default_factory=list)

    knowledge_scope: Optional[str] = None
    region: Optional[str] = None

    source_credibility: Optional[str] = None
    local_applicability: Optional[str] = None

    # -------------------------
    # Legal / regulatory metadata
    # -------------------------
    legal_status: Optional[str] = None
    effective_date: Optional[str] = None
    supersedes: List[str] = field(default_factory=list)
    amended_by: List[str] = field(default_factory=list)

    # -------------------------
    # Storage information
    # -------------------------
    raw_path: Optional[str] = None
    extracted_path: Optional[str] = None
    normalized_path: Optional[str] = None

    checksum: Optional[str] = None

    # -------------------------
    # Extraction information
    # -------------------------
    extraction_method: Optional[str] = None
    extracted_char_count: Optional[int] = None

    normalization_method: Optional[str] = None
    normalized_char_count: Optional[int] = None
    normalization_status: str = "PENDING"

    # -------------------------
    # Processing / quality state
    # -------------------------
    extraction_status: str = "PENDING"
    quality_status: str = "PENDING_REVIEW"

    review_notes: Optional[str] = None

    def to_dict(self):
        return asdict(self)
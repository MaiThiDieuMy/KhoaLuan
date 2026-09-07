import hashlib
import json
from pathlib import Path

import yaml


# ============================================================
# CONFIG
# ============================================================

BUNDLE_ID = "PESTICIDE_LIST_VN_CURRENT"

B06_BUCKET = "B06_PESTICIDE_LEGAL"


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

LEGAL_REGISTRY_FILE = Path(
    "src/agri_rag/config/legal_registry.yaml"
)

READINESS_FILE = Path(
    "data/agri_rag/registry/legal_bundle_readiness.json"
)

BUNDLE_DIR = Path(
    "data/agri_rag/legal_bundles"
) / BUNDLE_ID

MANIFEST_FILE = (
    BUNDLE_DIR
    / "manifest.json"
)


# ============================================================
# REQUIRED ROLES
#
# Đây là 5 nguồn nội dung chính.
# ============================================================

CONTENT_ROLES = [
    "BASE_INSTRUMENT_PDF",
    "BASE_ALLOWED_LIST",
    "BASE_BANNED_LIST",
    "AMENDMENT_INSTRUMENT_PDF",
    "AMENDMENT_APPENDICES",
]


# ============================================================
# PROVENANCE ROLES
#
# HTML notice để trace nguồn/công bố.
# Không dùng thay cho legal content chính.
# ============================================================

PROVENANCE_ROLES = [
    "BASE_INSTRUMENT_NOTICE",
    "AMENDMENT_INSTRUMENT_NOTICE",
]


# ============================================================
# IO
# ============================================================

def load_json(
    path: Path,
) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_json(
    path: Path,
    data: dict,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_yaml(
    path: Path,
) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return (
            yaml.safe_load(file)
            or {}
        )


# ============================================================
# CHECKSUM
# ============================================================

def sha256_file(
    path: Path,
) -> str:

    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:

        for block in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):

            hasher.update(
                block
            )

    return hasher.hexdigest()


# ============================================================
# ROLE INDEX
# ============================================================

def build_role_index(
    legal_registry: dict,
) -> dict:

    roles = (
        legal_registry.get(
            "document_roles"
        )
        or {}
    )

    result = {}

    for document_id, info in (
        roles.items()
    ):

        role = (
            info.get(
                "legal_role"
            )
        )

        if not role:
            continue

        result.setdefault(
            role,
            [],
        )

        result[
            role
        ].append(
            document_id
        )

    return result


# ============================================================
# LOAD ONE DOCUMENT AS BUNDLE MEMBER
# ============================================================

def build_member(
    document_id: str,
    expected_role: str,
    member_type: str,
) -> dict:

    registry_path = (
        DOCUMENT_DIR
        / f"{document_id}.json"
    )

    if not registry_path.exists():

        raise RuntimeError(
            f"{document_id}: "
            "document registry file not found."
        )

    document = load_json(
        registry_path
    )

    # ========================================================
    # UPSTREAM CHECKS
    # ========================================================

    if (
        document.get(
            "extraction_status"
        )
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: "
            "extraction is not SUCCESS."
        )

    if (
        document.get(
            "normalization_status"
        )
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: "
            "normalization is not SUCCESS."
        )

    if (
        document.get(
            "metadata_status"
        )
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: "
            "metadata is not SUCCESS."
        )

    if (
        document.get(
            "legal_validation_status"
        )
        != "VERIFIED"
    ):

        raise RuntimeError(
            f"{document_id}: "
            "legal validation is not VERIFIED."
        )

    # ========================================================
    # ROLE
    # ========================================================

    actual_role = (
        document.get(
            "legal_role"
        )
        or
        document.get(
            "legal_role_hint"
        )
    )

    if actual_role != expected_role:

        raise RuntimeError(
            f"{document_id}: "
            f"expected role={expected_role}, "
            f"actual={actual_role}."
        )

    # ========================================================
    # BUNDLE
    # ========================================================

    document_bundle_id = (
        document.get(
            "legal_bundle_id"
        )
    )

    if (
        document_bundle_id
        != BUNDLE_ID
    ):

        raise RuntimeError(
            f"{document_id}: "
            f"bundle mismatch "
            f"({document_bundle_id})."
        )

    # ========================================================
    # LEGAL BUCKET
    # ========================================================

    suggestions = (
        document.get(
            "suggested_buckets"
        )
        or []
    )

    if suggestions != [
        B06_BUCKET
    ]:

        raise RuntimeError(
            f"{document_id}: "
            "legal document must have "
            f"only suggested bucket {B06_BUCKET}."
        )

    # ========================================================
    # NORMALIZED FILE
    # ========================================================

    normalized_path_value = (
        document.get(
            "normalized_path"
        )
    )

    if not normalized_path_value:

        raise RuntimeError(
            f"{document_id}: "
            "normalized_path missing."
        )

    normalized_path = Path(
        normalized_path_value
    )

    if not normalized_path.exists():

        raise RuntimeError(
            f"{document_id}: "
            "normalized file not found."
        )

    # ========================================================
    # CHECKSUM
    #
    # Prefer the checksum produced by normalization stage.
    # Compute it again only as fallback.
    # ========================================================

    normalized_checksum = (
        document.get(
            "normalized_checksum"
        )
    )

    if not normalized_checksum:

        normalized_checksum = (
            sha256_file(
                normalized_path
            )
        )

    # ========================================================
    # RAW FILE
    # ========================================================

    raw_path_value = (
        document.get(
            "raw_path"
        )
    )

    raw_exists = False

    if raw_path_value:

        raw_exists = Path(
            raw_path_value
        ).exists()

    if not raw_exists:

        raise RuntimeError(
            f"{document_id}: "
            "raw evidence file not found."
        )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "document_id":
            document_id,

        "member_type":
            member_type,

        "legal_role":
            expected_role,

        "legal_identifier":
            (
                document.get(
                    "legal_identifier"
                )
                or
                document.get(
                    "legal_identifier_hint"
                )
            ),

        "legal_status":
            document.get(
                "legal_status"
            ),

        "effective_date":
            document.get(
                "effective_date"
            ),

        "published_date":
            document.get(
                "published_date"
            ),

        "document_family":
            document.get(
                "document_family"
            ),

        "knowledge_scope":
            document.get(
                "knowledge_scope"
            ),

        "source_id":
            document.get(
                "source_id"
            ),

        "source_credibility":
            document.get(
                "source_credibility"
            ),

        "url":
            document.get(
                "url"
            ),

        "raw_path":
            raw_path_value,

        "normalized_path":
            str(
                normalized_path
            ),

        "normalized_checksum":
            normalized_checksum,

        "normalized_char_count":
            document.get(
                "normalized_char_count"
            ),

        "legal_verified_on":
            document.get(
                "legal_verified_on"
            ),

        "legal_reverify_after":
            document.get(
                "legal_reverify_after"
            ),

        # ----------------------------------------------------
        # Legal docs are intentionally not direct RAG input.
        # ----------------------------------------------------

        "direct_rag_eligible":
            False,
    }


# ============================================================
# CONTENT FINGERPRINT
# ============================================================

def build_content_fingerprint(
    members: list,
) -> str:
    """
    Bundle fingerprint changes whenever one of the normalized
    legal source documents changes.

    This is useful later for:
    - reproducibility
    - RAGOps
    - detecting a new legal corpus version
    """

    rows = []

    for member in sorted(
        members,
        key=lambda item: (
            item[
                "legal_role"
            ],
            item[
                "document_id"
            ],
        ),
    ):

        rows.append(
            "|".join([
                member[
                    "legal_role"
                ],

                member[
                    "document_id"
                ],

                member[
                    "normalized_checksum"
                ],
            ])
        )

    payload = (
        "\n".join(
            rows
        )
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 78)
    print(
        "AGRI RAG - BUILD LEGAL BUNDLE MANIFEST"
    )
    print("=" * 78)

    # ========================================================
    # 1. READINESS
    # ========================================================

    if not READINESS_FILE.exists():

        raise RuntimeError(
            "Legal bundle readiness file "
            "does not exist. "
            "Run legal content completeness "
            "audit first."
        )

    readiness = load_json(
        READINESS_FILE
    )

    readiness_status = (
        readiness.get(
            "status"
        )
    )

    print(
        f"Bundle ID          : "
        f"{BUNDLE_ID}"
    )

    print(
        f"Readiness          : "
        f"{readiness_status}"
    )

    if readiness_status != "READY":

        raise RuntimeError(
            "Legal source corpus is not READY."
        )

    # ========================================================
    # 2. LEGAL REGISTRY
    # ========================================================

    legal_registry = load_yaml(
        LEGAL_REGISTRY_FILE
    )

    role_index = (
        build_role_index(
            legal_registry
        )
    )

    # ========================================================
    # 3. CONTENT MEMBERS
    # ========================================================

    content_members = []

    for role in CONTENT_ROLES:

        document_ids = (
            role_index.get(
                role,
                []
            )
        )

        if len(
            document_ids
        ) != 1:

            raise RuntimeError(
                f"Role {role}: expected exactly "
                f"1 document, found "
                f"{len(document_ids)}."
            )

        document_id = (
            document_ids[0]
        )

        member = build_member(
            document_id,
            role,
            "CONTENT",
        )

        content_members.append(
            member
        )

    # ========================================================
    # 4. PROVENANCE MEMBERS
    # ========================================================

    provenance_members = []

    for role in PROVENANCE_ROLES:

        document_ids = (
            role_index.get(
                role,
                []
            )
        )

        if len(
            document_ids
        ) != 1:

            raise RuntimeError(
                f"Role {role}: expected exactly "
                f"1 document, found "
                f"{len(document_ids)}."
            )

        document_id = (
            document_ids[0]
        )

        member = build_member(
            document_id,
            role,
            "PROVENANCE",
        )

        provenance_members.append(
            member
        )

    # ========================================================
    # 5. FINGERPRINT
    #
    # Provenance notice không làm thay đổi semantic
    # legal content fingerprint.
    # ========================================================

    content_fingerprint = (
        build_content_fingerprint(
            content_members
        )
    )

    # ========================================================
    # 6. LEGAL INSTRUMENTS
    # ========================================================

    instruments = (
        legal_registry.get(
            "legal_instruments"
        )
        or {}
    )

    tt75 = (
        instruments.get(
            "TT75_2025"
        )
        or {}
    )

    tt28 = (
        instruments.get(
            "TT28_2026"
        )
        or {}
    )

    # ========================================================
    # 7. MANIFEST
    # ========================================================

    manifest = {

        "bundle_id":
            BUNDLE_ID,

        "bundle_schema_version":
            "1.0",

        "bundle_type":
            "PESTICIDE_LEGAL_SOURCE_BUNDLE",

        "legal_snapshot_verified_on":
            legal_registry.get(
                "verified_on"
            ),

        # ----------------------------------------------------
        # Important:
        #
        # Source bundle is ready.
        # Current pesticide records are NOT yet consolidated.
        # ----------------------------------------------------

        "bundle_status":
            "READY_FOR_CONSOLIDATION",

        "consolidation_status":
            "NOT_STARTED",

        "rag_eligible":
            False,

        "rag_block_reason":
            "LEGAL_CONSOLIDATION_NOT_COMPLETED",

        "target_bucket":
            B06_BUCKET,

        # ----------------------------------------------------
        # Legal relationship
        # ----------------------------------------------------

        "base_instrument": {

            "registry_key":
                "TT75_2025",

            "identifier":
                tt75.get(
                    "identifier"
                ),

            "issued_date":
                tt75.get(
                    "issued_date"
                ),

            "effective_date":
                tt75.get(
                    "effective_date"
                ),

            "legal_status":
                tt75.get(
                    "legal_status"
                ),

            "amended_by":
                tt75.get(
                    "amended_by"
                )
                or [],
        },

        "effective_amendments": [

            {
                "registry_key":
                    "TT28_2026",

                "identifier":
                    tt28.get(
                        "identifier"
                    ),

                "issued_date":
                    tt28.get(
                        "issued_date"
                    ),

                "effective_date":
                    tt28.get(
                        "effective_date"
                    ),

                "legal_status":
                    tt28.get(
                        "legal_status"
                    ),

                "amends":
                    tt28.get(
                        "amends"
                    )
                    or [],
            }
        ],

        # ----------------------------------------------------
        # Five content documents
        # ----------------------------------------------------

        "content_members":
            content_members,

        # ----------------------------------------------------
        # Two HTML notices
        # ----------------------------------------------------

        "provenance_members":
            provenance_members,

        # ----------------------------------------------------
        # Reproducibility
        # ----------------------------------------------------

        "content_fingerprint_sha256":
            content_fingerprint,

        # ----------------------------------------------------
        # Safety policy
        # ----------------------------------------------------

        "usage_policy": {

            "direct_document_retrieval_allowed":
                False,

            "requires_consolidated_legal_records":
                True,

            "base_allowed_list_standalone_current":
                False,

            "apply_effective_amendments":
                True,

            "preserve_source_provenance":
                True,

            "require_current_status_before_recommendation":
                True,

            "llm_may_invent_legal_status":
                False,
        },

        # ----------------------------------------------------
        # Next processing stage
        # ----------------------------------------------------

        "next_stage": {

            "name":
                "LEGAL_RECORD_EXTRACTION_AND_CONSOLIDATION",

            "required_outputs": [
                "base_allowed_records",
                "base_banned_records",
                "amendment_change_records",
                "withdrawal_records",
                "addition_records",
                "current_consolidated_records",
            ],
        },

        "important_note": (
            "This manifest confirms the composition and "
            "traceability of the legal source bundle. "
            "It does not claim that the current pesticide "
            "list has already been consolidated."
        ),
    }

    # ========================================================
    # 8. SAVE
    # ========================================================

    save_json(
        MANIFEST_FILE,
        manifest,
    )

    # ========================================================
    # 9. OUTPUT
    # ========================================================

    print()
    print("-" * 78)
    print("CONTENT MEMBERS")
    print("-" * 78)

    for member in content_members:

        print(
            f"{member['document_id']:<8} "
            f"→ "
            f"{member['legal_role']:<30} "
            f"→ "
            f"{member['legal_identifier']}"
        )

    print()
    print("-" * 78)
    print("PROVENANCE MEMBERS")
    print("-" * 78)

    for member in provenance_members:

        print(
            f"{member['document_id']:<8} "
            f"→ "
            f"{member['legal_role']:<30} "
            f"→ "
            f"{member['legal_identifier']}"
        )

    print()
    print("=" * 78)
    print(
        "LEGAL BUNDLE MANIFEST SUMMARY"
    )
    print("=" * 78)

    print(
        f"Bundle ID           : "
        f"{BUNDLE_ID}"
    )

    print(
        f"Status              : "
        f"{manifest['bundle_status']}"
    )

    print(
        f"Content members     : "
        f"{len(content_members)}"
    )

    print(
        f"Provenance members  : "
        f"{len(provenance_members)}"
    )

    print(
        f"RAG eligible        : "
        f"{manifest['rag_eligible']}"
    )

    print(
        f"Consolidation       : "
        f"{manifest['consolidation_status']}"
    )

    print(
        f"Fingerprint         : "
        f"{content_fingerprint}"
    )

    print(
        f"Manifest            : "
        f"{MANIFEST_FILE}"
    )

    print()

    print(
        "Legal bundle manifest created successfully."
    )

    print(
        "Current pesticide records have NOT "
        "yet been consolidated."
    )


if __name__ == "__main__":
    main()
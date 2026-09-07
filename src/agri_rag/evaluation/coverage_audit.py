import csv
import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

REGISTRY_DIR = Path(
    "data/agri_rag/registry"
)

DOCUMENT_DIR = (
    REGISTRY_DIR
    / "documents"
)

SECTION_DIR = (
    REGISTRY_DIR
    / "sections"
)

ACCEPTED_MANIFEST = (
    REGISTRY_DIR
    / "accepted_manifest.jsonl"
)

REVIEW_MANIFEST = (
    REGISTRY_DIR
    / "review_manifest.jsonl"
)

REJECTED_MANIFEST = (
    REGISTRY_DIR
    / "rejected_manifest.jsonl"
)

LEGAL_BUNDLE_MANIFEST = Path(
    "data/agri_rag/legal_bundles/"
    "PESTICIDE_LIST_VN_CURRENT/"
    "manifest.json"
)

LEGAL_READINESS_FILE = (
    REGISTRY_DIR
    / "legal_bundle_readiness.json"
)

COVERAGE_REPORT = (
    REGISTRY_DIR
    / "coverage_report.csv"
)

COVERAGE_SUMMARY = (
    REGISTRY_DIR
    / "coverage_summary.json"
)


# ============================================================
# CROPS
# ============================================================

CROPS = {
    "cai_xanh":
        "Cải xanh",

    "ngo":
        "Ngò / ngò rí",

    "cai_cuc":
        "Cải cúc / tần ô",

    "rau_muong":
        "Rau muống",

    "xa_lach":
        "Xà lách",
}


# ============================================================
# BUCKETS
# ============================================================

BUCKETS = [
    "B01_CROP_PROFILE",
    "B02_WATER",
    "B03_NUTRITION",
    "B04_PEST_DISEASE",
    "B05_WEATHER_CARE",
    "B06_PESTICIDE_LEGAL",
    "B07_GAP_SAFETY",
    "B08_LOCAL",
]

CORE_BUCKETS = [
    "B01_CROP_PROFILE",
    "B02_WATER",
    "B03_NUTRITION",
    "B04_PEST_DISEASE",
    "B05_WEATHER_CARE",
]

BUCKET_LABELS = {
    "B01_CROP_PROFILE":
        "Crop Profile",

    "B02_WATER":
        "Water",

    "B03_NUTRITION":
        "Nutrition",

    "B04_PEST_DISEASE":
        "Pest & Disease",

    "B05_WEATHER_CARE":
        "Weather Care",

    "B06_PESTICIDE_LEGAL":
        "Pesticide Legal",

    "B07_GAP_SAFETY":
        "GAP & Safety",

    "B08_LOCAL":
        "Local",
}


# ============================================================
# IO
# ============================================================

def load_json(
    path: Path,
):

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(
            file
        )


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


# ============================================================
# HELPERS
# ============================================================

def as_list(
    value,
):

    if value is None:

        return []

    if isinstance(
        value,
        list,
    ):

        return value

    if isinstance(
        value,
        tuple,
    ):

        return list(
            value
        )

    if isinstance(
        value,
        str,
    ):

        value = (
            value.strip()
        )

        if not value:

            return []

        return [
            value
        ]

    return []


def unique_sorted(
    values,
):

    return sorted(
        {
            value

            for value in values

            if value
        }
    )


# ============================================================
# MANIFEST DOCUMENT ID
# ============================================================

def find_document_id(
    value,
):

    if isinstance(
        value,
        dict,
    ):

        # Prefer explicit document_id.
        if value.get(
            "document_id"
        ):

            return str(
                value[
                    "document_id"
                ]
            )

        # Some manifests may use id.
        candidate = (
            value.get(
                "id"
            )
        )

        if (
            isinstance(
                candidate,
                str,
            )
            and
            candidate.startswith(
                "DOC"
            )
        ):

            return candidate

        for nested in (
            value.values()
        ):

            result = (
                find_document_id(
                    nested
                )
            )

            if result:

                return result

    elif isinstance(
        value,
        list,
    ):

        for nested in value:

            result = (
                find_document_id(
                    nested
                )
            )

            if result:

                return result

    return None


# ============================================================
# LOAD QUALITY MANIFEST
# ============================================================

def load_manifest_ids(
    path: Path,
):

    ids = set()

    if not path.exists():

        return ids

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            line = (
                line.strip()
            )

            if not line:

                continue

            try:

                record = (
                    json.loads(
                        line
                    )
                )

            except Exception as exc:

                print(
                    f"[WARN] "
                    f"{path.name} line "
                    f"{line_number}: {exc}"
                )

                continue

            document_id = (
                find_document_id(
                    record
                )
            )

            if document_id:

                ids.add(
                    document_id
                )

    return ids


# ============================================================
# LOAD DOCUMENT REGISTRY
# ============================================================

def load_documents():

    documents = {}

    if not (
        DOCUMENT_DIR.exists()
    ):

        return documents

    for path in sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    ):

        try:

            record = (
                load_json(
                    path
                )
            )

        except Exception as exc:

            print(
                f"[WARN] Cannot load "
                f"{path}: {exc}"
            )

            continue

        document_id = (
            record.get(
                "document_id"
            )
            or
            path.stem
        )

        documents[
            document_id
        ] = record

    return documents


# ============================================================
# LOAD SECTION REGISTRY
# ============================================================

def load_sections():

    sections = []

    if not (
        SECTION_DIR.exists()
    ):

        return sections

    for path in sorted(
        SECTION_DIR.glob(
            "SEC*.json"
        )
    ):

        try:

            sections.append(
                load_json(
                    path
                )
            )

        except Exception as exc:

            print(
                f"[WARN] Cannot load "
                f"{path}: {exc}"
            )

    return sections


# ============================================================
# DOCUMENT METADATA
# ============================================================

def document_crops(
    record: dict,
):

    return as_list(
        record.get(
            "crop_entities"
        )
    )


def document_buckets(
    record: dict,
):

    return as_list(
        record.get(
            "buckets"
        )
    )


def document_scope(
    record: dict,
):

    return str(
        record.get(
            "knowledge_scope",
            "",
        )
        or ""
    ).lower()


def document_source(
    record: dict,
):

    return str(
        record.get(
            "source_id",
            "",
        )
        or ""
    )


# ============================================================
# ACCEPTED DOCUMENT EVIDENCE
#
# IMPORTANT:
#
# Quality status is determined from accepted_manifest.jsonl.
# We deliberately DO NOT require:
#
#     quality_status == ACCEPTED
#
# because existing document JSON files contain the older
# PENDING_REVIEW metadata even though the Quality Gate has
# already accepted them.
#
# Manifest = final Quality Gate decision.
# JSON metadata = evidence metadata.
# ============================================================

def document_is_accepted_evidence(
    document_id: str,
    record: dict,
    accepted_ids: set,
    crop_id: str,
    bucket: str,
):

    if (
        document_id
        not in accepted_ids
    ):

        return False

    # Explicit rag_eligible=False still blocks usage.
    if (
        record.get(
            "rag_eligible"
        )
        is False
    ):

        return False

    if (
        crop_id
        not in document_crops(
            record
        )
    ):

        return False

    if (
        bucket
        not in document_buckets(
            record
        )
    ):

        return False

    # Conservative document-level coverage.
    #
    # General agronomy documents must not automatically
    # become crop-specific evidence.
    if (
        document_scope(
            record
        )
        != "crop_specific"
    ):

        return False

    return True


# ============================================================
# REVIEW DOCUMENT EVIDENCE
# ============================================================

def document_is_review_candidate(
    document_id: str,
    record: dict,
    review_ids: set,
    crop_id: str,
    bucket: str,
):

    if (
        document_id
        not in review_ids
    ):

        return False

    if (
        crop_id
        not in document_crops(
            record
        )
    ):

        return False

    if (
        bucket
        not in document_buckets(
            record
        )
    ):

        return False

    return True


# ============================================================
# SECTION EVIDENCE
# ============================================================

def section_is_accepted(
    record: dict,
    crop_id: str,
    bucket: str,
):

    if (
        str(
            record.get(
                "evidence_status",
                "",
            )
        ).upper()
        != "ACCEPTED_SECTION"
    ):

        return False

    if not (
        record.get(
            "coverage_eligible",
            False,
        )
    ):

        return False

    if (
        crop_id
        not in as_list(
            record.get(
                "crop_entities"
            )
        )
    ):

        return False

    if (
        bucket
        not in as_list(
            record.get(
                "buckets"
            )
        )
    ):

        return False

    return True


def section_is_review(
    record: dict,
    crop_id: str,
    bucket: str,
):

    if (
        str(
            record.get(
                "evidence_status",
                "",
            )
        ).upper()
        != "REVIEW_REQUIRED"
    ):

        return False

    if (
        crop_id
        not in as_list(
            record.get(
                "crop_entities"
            )
        )
    ):

        return False

    if (
        bucket
        not in as_list(
            record.get(
                "buckets"
            )
        )
    ):

        return False

    return True


# ============================================================
# LEGAL HELPERS
# ============================================================

def contains_token_recursive(
    value,
    token: str,
):

    token = str(
        token
    ).strip().upper()

    if isinstance(
        value,
        dict,
    ):

        return any(
            contains_token_recursive(
                item,
                token,
            )

            for item
            in value.values()
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return any(
            contains_token_recursive(
                item,
                token,
            )

            for item
            in value
        )

    if value is None:

        return False

    return (
        str(
            value
        ).strip().upper()
        ==
        token
    )
# ============================================================
# LEGAL STATE
# ============================================================

def get_legal_state():

    manifest = {}
    readiness = {}

    if LEGAL_BUNDLE_MANIFEST.exists():

        manifest = load_json(
            LEGAL_BUNDLE_MANIFEST
        )

    if LEGAL_READINESS_FILE.exists():

        readiness = load_json(
            LEGAL_READINESS_FILE
        )

    consolidation = (
        manifest.get(
            "consolidation",
            {},
        )
    )

    if not isinstance(
        consolidation,
        dict,
    ):

        consolidation = {}

    current_records = (
        manifest.get(
            "current_legal_records",
            {},
        )
    )

    if not isinstance(
        current_records,
        dict,
    ):

        current_records = {}

    consolidation_status = str(
        manifest.get(
            "consolidation_status",
            "",
        )
    ).strip().upper()

    nested_status = str(
        consolidation.get(
            "status",
            "",
        )
    ).strip().upper()

    consolidation_completed = (
        consolidation_status
        == "COMPLETED"
        and
        nested_status
        == "COMPLETED"
    )

    structural_passed = (
        consolidation.get(
            "structural_audit_passed"
        )
        is True
    )

    human_approved = (
        consolidation.get(
            "human_approved"
        )
        is True
    )

    runtime_eligible = (
        consolidation.get(
            "runtime_eligible"
        )
        is True
        and
        current_records.get(
            "runtime_eligible"
        )
        is True
    )

    legal_current_ready = (
        manifest.get(
            "legal_current_ready"
        )
        is True
    )

    # Raw legal source bundle must stay isolated from
    # normal RAG retrieval even after consolidation.
    raw_bundle_rag_eligible = (
        manifest.get(
            "rag_eligible"
        )
        is True
    )

    record_count = (
        consolidation.get(
            "record_count",
            0,
        )
    )

    active_record_count = (
        consolidation.get(
            "active_record_count",
            0,
        )
    )

    try:

        record_count = int(
            record_count
        )

    except (
        TypeError,
        ValueError,
    ):

        record_count = 0

    try:

        active_record_count = int(
            active_record_count
        )

    except (
        TypeError,
        ValueError,
    ):

        active_record_count = 0

    output_value = str(
        consolidation.get(
            "output",
            "",
        )
        or ""
    ).strip()

    current_records_exist = (
        bool(
            output_value
        )
        and
        Path(
            output_value
        ).exists()
    )

    current_ready = all([
        consolidation_completed,
        structural_passed,
        human_approved,
        runtime_eligible,
        legal_current_ready,
        current_records_exist,
        record_count > 0,
        active_record_count > 0,
    ])

    if current_ready:

        return {
            "status":
                "LEGAL_CURRENT_READY",

            "code":
                "LEGAL",

            "reason":
                "CURRENT_LEGAL_RECORDS_CONSOLIDATED_AND_APPROVED",

            "next_action":
                "NONE",

            "source_ready":
                True,

            "current_ready":
                True,

            "record_count":
                record_count,

            "active_record_count":
                active_record_count,

            "raw_bundle_rag_eligible":
                raw_bundle_rag_eligible,

            "runtime_source":
                output_value,
        }

    # --------------------------------------------------------
    # Source bundle readiness.
    #
    # Exact-token checks only.
    # "READY" no longer matches "NOT_READY".
    # --------------------------------------------------------

    source_ready = (
        contains_token_recursive(
            manifest,
            "READY_FOR_CONSOLIDATION",
        )
        or
        contains_token_recursive(
            readiness,
            "READY",
        )
    )

    if (
        structural_passed
        and
        consolidation_status
        == "PENDING_HUMAN_APPROVAL"
    ):

        return {
            "status":
                "LEGAL_CONSOLIDATION_PENDING_APPROVAL",

            "code":
                "L-SRC",

            "reason":
                "LEGAL_RECORDS_STRUCTURALLY_VALIDATED_PENDING_APPROVAL",

            "next_action":
                "APPROVE_LEGAL_CONSOLIDATION",

            "source_ready":
                True,

            "current_ready":
                False,

            "raw_bundle_rag_eligible":
                raw_bundle_rag_eligible,
        }

    if (
        consolidation_status
        == "REVIEW_REQUIRED"
    ):

        return {
            "status":
                "LEGAL_CONSOLIDATION_REVIEW_REQUIRED",

            "code":
                "L-SRC",

            "reason":
                "LEGAL_CONSOLIDATION_HAS_BLOCKING_ISSUES",

            "next_action":
                "FIX_LEGAL_CONSOLIDATION",

            "source_ready":
                source_ready,

            "current_ready":
                False,

            "raw_bundle_rag_eligible":
                raw_bundle_rag_eligible,
        }

    if source_ready:

        return {
            "status":
                "LEGAL_SOURCE_READY",

            "code":
                "L-SRC",

            "reason":
                "LEGAL_SOURCE_COMPLETE_BUT_NOT_CONSOLIDATED",

            "next_action":
                "RUN_LEGAL_CONSOLIDATION",

            "source_ready":
                True,

            "current_ready":
                False,

            "raw_bundle_rag_eligible":
                raw_bundle_rag_eligible,
        }

    return {
        "status":
            "LEGAL_NOT_READY",

        "code":
            "L-NO",

        "reason":
            "LEGAL_SOURCE_PIPELINE_NOT_READY",

        "next_action":
            "COMPLETE_LEGAL_SOURCE_PIPELINE",

        "source_ready":
            False,

        "current_ready":
            False,

        "raw_bundle_rag_eligible":
            raw_bundle_rag_eligible,
    }
# ============================================================
# COLLECT CELL EVIDENCE
# ============================================================

def collect_cell_evidence(
    documents: dict,
    sections: list,
    accepted_ids: set,
    review_ids: set,
    crop_id: str,
    bucket: str,
):

    accepted_documents = []

    accepted_sections = []

    review_documents = []

    review_sections = []

    sources = []

    # ========================================================
    # DOCUMENTS
    # ========================================================

    for (
        document_id,
        record,
    ) in documents.items():

        if document_is_accepted_evidence(
            document_id,
            record,
            accepted_ids,
            crop_id,
            bucket,
        ):

            accepted_documents.append(
                document_id
            )

            source_id = (
                document_source(
                    record
                )
            )

            if source_id:

                sources.append(
                    source_id
                )

        elif document_is_review_candidate(
            document_id,
            record,
            review_ids,
            crop_id,
            bucket,
        ):

            review_documents.append(
                document_id
            )

    # ========================================================
    # SECTIONS
    # ========================================================

    for record in sections:

        if section_is_accepted(
            record,
            crop_id,
            bucket,
        ):

            accepted_sections.append(
                record.get(
                    "section_id",
                    "",
                )
            )

            source_id = (
                record.get(
                    "source_id",
                    ""
                )
            )

            if source_id:

                sources.append(
                    source_id
                )

        elif section_is_review(
            record,
            crop_id,
            bucket,
        ):

            review_sections.append(
                record.get(
                    "section_id",
                    "",
                )
            )

    accepted_documents = (
        unique_sorted(
            accepted_documents
        )
    )

    accepted_sections = (
        unique_sorted(
            accepted_sections
        )
    )

    review_documents = (
        unique_sorted(
            review_documents
        )
    )

    review_sections = (
        unique_sorted(
            review_sections
        )
    )

    sources = (
        unique_sorted(
            sources
        )
    )

    evidence_count = (
        len(
            accepted_documents
        )
        +
        len(
            accepted_sections
        )
    )

    review_count = (
        len(
            review_documents
        )
        +
        len(
            review_sections
        )
    )

    if (
        len(
            sources
        )
        >= 2
    ):

        status = (
            "MULTI_SOURCE_READY"
        )

        code = (
            "R2+"
        )

    elif (
        evidence_count
        >= 1
    ):

        status = (
            "EVIDENCE_READY"
        )

        code = (
            "R1"
        )

    elif (
        review_count
        >= 1
    ):

        status = (
            "REVIEW_CANDIDATE"
        )

        code = (
            "REV"
        )

    else:

        status = (
            "MISSING"
        )

        code = (
            "--"
        )

    return {
        "status":
            status,

        "code":
            code,

        "accepted_documents":
            accepted_documents,

        "accepted_sections":
            accepted_sections,

        "review_documents":
            review_documents,

        "review_sections":
            review_sections,

        "source_ids":
            sources,

        "evidence_count":
            evidence_count,

        "source_count":
            len(
                sources
            ),
    }


# ============================================================
# BUILD MATRIX
# ============================================================

def build_coverage(
    documents: dict,
    sections: list,
    accepted_ids: set,
    review_ids: set,
    legal_state: dict,
):

    matrix = {}

    rows = []

    for (
        crop_id,
        crop_name,
    ) in CROPS.items():

        matrix[
            crop_id
        ] = {}

        for bucket in BUCKETS:

            if (
                bucket
                ==
                "B06_PESTICIDE_LEGAL"
            ):

                cell = {
                    "status":
                        legal_state[
                            "status"
                        ],

                    "code":
                        legal_state[
                            "code"
                        ],

                    "accepted_documents":
                        [],

                    "accepted_sections":
                        [],

                    "review_documents":
                        [],

                    "review_sections":
                        [],

                    "source_ids": [
                        "PESTICIDE_LIST_VN_CURRENT"
                    ],

                    "evidence_count":
                        0,

                    "source_count":
                        1,
                }

            else:

                cell = (
                    collect_cell_evidence(
                        documents,
                        sections,
                        accepted_ids,
                        review_ids,
                        crop_id,
                        bucket,
                    )
                )

            matrix[
                crop_id
            ][
                bucket
            ] = cell

            rows.append({
                "crop_id":
                    crop_id,

                "crop_name":
                    crop_name,

                "bucket":
                    bucket,

                "bucket_label":
                    BUCKET_LABELS[
                        bucket
                    ],

                "status":
                    cell[
                        "status"
                    ],

                "code":
                    cell[
                        "code"
                    ],

                "evidence_count":
                    cell[
                        "evidence_count"
                    ],

                "source_count":
                    cell[
                        "source_count"
                    ],

                "source_ids":
                    "|".join(
                        cell[
                            "source_ids"
                        ]
                    ),

                "accepted_documents":
                    "|".join(
                        cell[
                            "accepted_documents"
                        ]
                    ),

                "accepted_sections":
                    "|".join(
                        cell[
                            "accepted_sections"
                        ]
                    ),

                "review_documents":
                    "|".join(
                        cell[
                            "review_documents"
                        ]
                    ),

                "review_sections":
                    "|".join(
                        cell[
                            "review_sections"
                        ]
                    ),
            })

    return (
        matrix,
        rows,
    )


# ============================================================
# PRINT MATRIX
# ============================================================

def print_matrix(
    matrix: dict,
):

    print()
    print("=" * 100)
    print(
        "CROP × KNOWLEDGE COVERAGE MATRIX"
    )
    print("=" * 100)

    print(
        f"{'Crop':<25}"
        f"{'B01':>9}"
        f"{'B02':>9}"
        f"{'B03':>9}"
        f"{'B04':>9}"
        f"{'B05':>9}"
        f"{'B06':>9}"
        f"{'B07':>9}"
        f"{'B08':>9}"
    )

    print("-" * 100)

    for (
        crop_id,
        crop_name,
    ) in CROPS.items():

        codes = [

            matrix[
                crop_id
            ][
                bucket
            ][
                "code"
            ]

            for bucket
            in BUCKETS
        ]

        print(
            f"{crop_name:<25}"
            +
            "".join(
                f"{code:>9}"
                for code
                in codes
            )
        )

    print()
    print("Legend:")
    print(
        "  R2+   = accepted evidence from >=2 independent source IDs"
    )
    print(
        "  R1    = >=1 accepted document/section evidence"
    )
    print(
        "  REV   = only review candidate exists"
    )
    print(
        "  --    = no accepted crop-specific evidence"
    )
    print(
        "  L-SRC = legal source bundle ready; consolidation pending"
    )
    print(
        "  LEGAL = consolidated current Vietnamese legal records ready"
    )
    print(
        "  L-NO  = legal source pipeline not ready"
    )


# ============================================================
# CORE SUMMARY
# ============================================================

def build_core_summary(
    matrix: dict,
):

    total = (
        len(
            CROPS
        )
        *
        len(
            CORE_BUCKETS
        )
    )

    ready = 0

    multi_source = 0

    review_only = 0

    missing = 0

    per_crop = {}

    gaps = []

    for (
        crop_id,
        crop_name,
    ) in CROPS.items():

        crop_ready = 0

        crop_review = 0

        crop_missing = 0

        for bucket in (
            CORE_BUCKETS
        ):

            code = (
                matrix[
                    crop_id
                ][
                    bucket
                ][
                    "code"
                ]
            )

            if code in {
                "R1",
                "R2+",
            }:

                ready += 1

                crop_ready += 1

                if (
                    code
                    == "R2+"
                ):

                    multi_source += 1

            elif (
                code
                == "REV"
            ):

                review_only += 1

                crop_review += 1

                gaps.append({
                    "crop_id":
                        crop_id,

                    "crop_name":
                        crop_name,

                    "bucket":
                        bucket,

                    "bucket_label":
                        BUCKET_LABELS[
                            bucket
                        ],

                    "status":
                        "REVIEW_ONLY",
                })

            else:

                missing += 1

                crop_missing += 1

                gaps.append({
                    "crop_id":
                        crop_id,

                    "crop_name":
                        crop_name,

                    "bucket":
                        bucket,

                    "bucket_label":
                        BUCKET_LABELS[
                            bucket
                        ],

                    "status":
                        "MISSING",
                })

        per_crop[
            crop_id
        ] = {
            "crop_name":
                crop_name,

            "ready":
                crop_ready,

            "review":
                crop_review,

            "missing":
                crop_missing,
        }

    all_ready_crop_count = sum(

        1

        for info
        in per_crop.values()

        if (
            info[
                "ready"
            ]
            ==
            len(
                CORE_BUCKETS
            )
        )
    )

    return {
        "target_crop_count":
            len(
                CROPS
            ),

        "core_cells_total":
            total,

        "core_ready_cells":
            ready,

        "core_coverage_percent":
            round(
                (
                    ready
                    / total
                    * 100
                ),
                1,
            ),

        "multi_source_core_cells":
            multi_source,

        "multi_source_coverage_percent":
            round(
                (
                    multi_source
                    / total
                    * 100
                ),
                1,
            ),

        "review_only_core_cells":
            review_only,

        "missing_core_cells":
            missing,

        "crops_with_all_core_ready":
            all_ready_crop_count,

        "per_crop":
            per_crop,

        "high_priority_gaps":
            gaps,

        "agronomy_core_ready":
            (
                ready == total
                and
                review_only == 0
                and
                missing == 0
            ),
    }


# ============================================================
# PRINT CORE SUMMARY
# ============================================================

def print_core_summary(
    summary: dict,
):

    print()
    print("=" * 100)
    print(
        "CORE AGRONOMY COVERAGE SUMMARY"
    )
    print("=" * 100)

    print(
        f"Target crops                   : "
        f"{summary['target_crop_count']}"
    )

    print(
        f"Core buckets per crop          : "
        f"{len(CORE_BUCKETS)}"
    )

    print(
        f"Core cells total               : "
        f"{summary['core_cells_total']}"
    )

    print(
        f"Evidence-ready core cells      : "
        f"{summary['core_ready_cells']}"
    )

    print(
        f"Core coverage                  : "
        f"{summary['core_coverage_percent']:.1f}%"
    )

    print(
        f"Multi-source core cells        : "
        f"{summary['multi_source_core_cells']}"
    )

    print(
        f"Multi-source coverage          : "
        f"{summary['multi_source_coverage_percent']:.1f}%"
    )

    print(
        f"Review-only core cells         : "
        f"{summary['review_only_core_cells']}"
    )

    print(
        f"Missing core cells             : "
        f"{summary['missing_core_cells']}"
    )

    print(
        f"Crops with all B01-B05 ready   : "
        f"{summary['crops_with_all_core_ready']}"
        f"/"
        f"{summary['target_crop_count']}"
    )

    print()
    print("=" * 100)
    print(
        "PER-CROP CORE COVERAGE"
    )
    print("=" * 100)

    for crop_id in CROPS:

        info = (
            summary[
                "per_crop"
            ][
                crop_id
            ]
        )

        print(
            f"{info['crop_name']:<25}: "
            f"{info['ready']}/5 ready, "
            f"{info['review']} review, "
            f"{info['missing']} missing"
        )


# ============================================================
# PRINT LEGAL
# ============================================================

def print_legal(
    legal_state: dict,
):

    print()
    print("=" * 100)
    print(
        "LEGAL COVERAGE"
    )
    print("=" * 100)

    print(
        f"Status      : "
        f"{legal_state['status']}"
    )

    print(
        f"Reason      : "
        f"{legal_state['reason']}"
    )

    print(
        f"Next action : "
        f"{legal_state['next_action']}"
    )


# ============================================================
# PRINT GAPS
# ============================================================

def print_gaps(
    core_summary: dict,
):

    print()
    print("=" * 100)
    print(
        "HIGH-PRIORITY CORE KNOWLEDGE GAPS"
    )
    print("=" * 100)

    gaps = (
        core_summary[
            "high_priority_gaps"
        ]
    )

    if not gaps:

        print()
        print(
            "None. All 25 B01-B05 crop cells "
            "have accepted evidence."
        )

        return

    current_crop = None

    for gap in gaps:

        if (
            current_crop
            != gap[
                "crop_id"
            ]
        ):

            current_crop = (
                gap[
                    "crop_id"
                ]
            )

            print()
            print(
                f"{gap['crop_name']} "
                f"({gap['crop_id']})"
            )

        print(
            f"  - "
            f"{gap['bucket']} "
            f"{gap['bucket_label']} "
            f"[{gap['status']}]"
        )


# ============================================================
# SUFFICIENCY DECISION
# ============================================================

def build_decision(
    core_summary: dict,
    legal_state: dict,
):

    agronomy_ready = (
        core_summary[
            "agronomy_core_ready"
        ]
    )

    legal_ready = (
        legal_state[
            "current_ready"
        ]
    )

    if (
        agronomy_ready
        and
        legal_ready
    ):

        return {
            "status":
                "CORE_KNOWLEDGE_READY",

            "final_kb_ready":
                False,

            "messages": [
                (
                    "All 25 B01-B05 crop cells "
                    "have accepted evidence."
                ),
                (
                    "B06 consolidated current Vietnamese "
                    "legal records are ready."
                ),
                (
                    "Proceed to corpus sectioning/chunking "
                    "and retrieval evaluation."
                ),
            ],
        }

    if (
        agronomy_ready
        and
        not legal_ready
    ):

        return {
            "status":
                "AGRONOMY_CORE_READY_LEGAL_PENDING",

            "final_kb_ready":
                False,

            "messages": [
                (
                    "All 25 B01-B05 crop cells now have "
                    "accepted document/section evidence."
                ),
                (
                    "No additional core agronomy source "
                    "acquisition is currently required."
                ),
                (
                    "B06 legal source bundle is ready, "
                    "but current pesticide records still "
                    "require legal consolidation."
                ),
            ],
        }

    return {
        "status":
            "NOT_SUFFICIENT",

        "final_kb_ready":
            False,

        "messages": [
            (
                "One or more B01-B05 crop cells still "
                "lack accepted evidence."
            ),
            (
                "Resolve only the reported gaps before "
                "final RAG indexing."
            ),
        ],
    }


def print_decision(
    decision: dict,
):

    print()
    print("=" * 100)
    print(
        "DATA SUFFICIENCY DECISION"
    )
    print("=" * 100)

    print(
        f"Overall status : "
        f"{decision['status']}"
    )

    print()

    for message in (
        decision[
            "messages"
        ]
    ):

        print(
            f"- {message}"
        )


# ============================================================
# SAVE CSV
# ============================================================

def save_report(
    rows: list,
):

    fieldnames = [
        "crop_id",
        "crop_name",
        "bucket",
        "bucket_label",
        "status",
        "code",
        "evidence_count",
        "source_count",
        "source_ids",
        "accepted_documents",
        "accepted_sections",
        "review_documents",
        "review_sections",
    ]

    with COVERAGE_REPORT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = (
            csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)
    print(
        "AGRI RAG - UNIFIED KNOWLEDGE COVERAGE AUDIT"
    )
    print("=" * 100)

    documents = (
        load_documents()
    )

    sections = (
        load_sections()
    )

    accepted_ids = (
        load_manifest_ids(
            ACCEPTED_MANIFEST
        )
    )

    review_ids = (
        load_manifest_ids(
            REVIEW_MANIFEST
        )
    )

    rejected_ids = (
        load_manifest_ids(
            REJECTED_MANIFEST
        )
    )

    legal_state = (
        get_legal_state()
    )

    print(
        f"Documents loaded              : "
        f"{len(documents)}"
    )

    print(
        f"Sections loaded               : "
        f"{len(sections)}"
    )

    print(
        f"Quality Gate accepted docs    : "
        f"{len(accepted_ids)}"
    )

    print(
        f"Quality Gate review docs      : "
        f"{len(review_ids)}"
    )

    print(
        f"Quality Gate rejected docs    : "
        f"{len(rejected_ids)}"
    )

    # ========================================================
    # SANITY CHECK
    # ========================================================

    overlap = (
        accepted_ids
        &
        review_ids
    )

    overlap |= (
        accepted_ids
        &
        rejected_ids
    )

    overlap |= (
        review_ids
        &
        rejected_ids
    )

    if overlap:

        raise RuntimeError(
            "Quality manifests overlap for documents: "
            f"{sorted(overlap)}"
        )

    (
        matrix,
        rows,
    ) = build_coverage(
        documents,
        sections,
        accepted_ids,
        review_ids,
        legal_state,
    )

    print_matrix(
        matrix
    )

    core_summary = (
        build_core_summary(
            matrix
        )
    )

    print_core_summary(
        core_summary
    )

    print_legal(
        legal_state
    )

    print_gaps(
        core_summary
    )

    decision = (
        build_decision(
            core_summary,
            legal_state,
        )
    )

    print_decision(
        decision
    )

    save_report(
        rows
    )

    summary = {
        "documents_loaded":
            len(
                documents
            ),

        "sections_loaded":
            len(
                sections
            ),

        "quality_gate": {
            "accepted":
                sorted(
                    accepted_ids
                ),

            "review":
                sorted(
                    review_ids
                ),

            "rejected":
                sorted(
                    rejected_ids
                ),
        },

        "core_summary":
            core_summary,

        "legal":
            legal_state,

        "decision":
            decision,

        "matrix":
            matrix,
    }

    save_json(
        COVERAGE_SUMMARY,
        summary,
    )

    print()
    print("=" * 100)
    print(
        "OUTPUT"
    )
    print("=" * 100)

    print(
        f"Coverage report : "
        f"{COVERAGE_REPORT}"
    )

    print(
        f"Summary         : "
        f"{COVERAGE_SUMMARY}"
    )

    print()
    print(
        "NOTE:"
    )

    print(
        "- Document acceptance comes from the "
        "Quality Gate manifests."
    )

    print(
        "- Crop/bucket/source metadata comes from "
        "the document registry."
    )

    print(
        "- Validated section evidence is combined "
        "with accepted document evidence."
    )

    print(
        "- B06 remains isolated in the Vietnamese "
        "legal consolidation pipeline."
    )

    print(
        "- R1/R2+ measure evidence coverage, "
        "not retrieval quality or field efficacy."
    )


if __name__ == "__main__":
    main()
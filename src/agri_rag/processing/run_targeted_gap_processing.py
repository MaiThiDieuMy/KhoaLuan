import hashlib
import json
import re
import unicodedata
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

SECTION_TEXT_DIR = Path(
    "data/agri_rag/sections"
)

SECTION_REGISTRY_DIR = Path(
    "data/agri_rag/registry/sections"
)

SUMMARY_FILE = Path(
    "data/agri_rag/registry/targeted_gap_processing_summary.json"
)


# ============================================================
# TARGET CROPS
# ============================================================

CROP_NGO = "ngo"
CROP_CAI_CUC = "cai_cuc"


# ============================================================
# BUCKETS
# ============================================================

B01 = "B01_CROP_PROFILE"
B02 = "B02_WATER"
B03 = "B03_NUTRITION"
B04 = "B04_PEST_DISEASE"
B05 = "B05_WEATHER_CARE"


# ============================================================
# TARGET CONFIG
#
# Important:
# - Bucket assignment is evidence-driven.
# - Do not assign all buckets merely because a crop name exists.
# - Agronomy sources never authorize pesticide legality.
# - B06 remains isolated in the legal pipeline.
# ============================================================

TARGETS = {

    # ========================================================
    # NGÒ - VIETNAM SOURCE
    # ========================================================

    "SEC0017_NGO_CTU": {

        "parent_document_id":
            "DOC0017",

        "source_id":
            "S07_CTU",

        "crop_id":
            CROP_NGO,

        "crop_name":
            "Ngò / ngò rí",

        "section_mode":
            "FULL_DOCUMENT",

        "knowledge_scope":
            "crop_specific",

        "region":
            "VIETNAM",

        "local_applicability":
            "VIETNAM_GENERAL",

        "evidence_role":
            "PRIMARY_VIETNAM_AGRONOMY",

        "buckets": [
            B01,
            B02,
            B03,
            B05,
        ],

        "bucket_markers": {

            B01: [
                [
                    "ngò rí",
                    "coriandrum",
                ],
                [
                    "mùa vụ",
                    "thời gian sinh trưởng",
                    "thu hoạch",
                ],
            ],

            B02: [
                [
                    "tưới nước",
                ],
                [
                    "thoát nước",
                    "ngập nước",
                    "ngập úng",
                ],
            ],

            B03: [
                [
                    "phân bón",
                ],
                [
                    "bón lót",
                    "urea",
                    "npk",
                    "dap",
                ],
            ],

            B05: [
                [
                    "khí hậu",
                ],
                [
                    "mưa nhiều",
                    "mùa mưa",
                    "mùa khô",
                    "gió nóng",
                ],
            ],
        },

        "safety_notes": [
            (
                "Any pesticide names appearing in this agronomy "
                "article are NOT treated as current Vietnamese "
                "legal authorization. B06 must use the separate "
                "Vietnam legal pipeline."
            )
        ],
    },


    # ========================================================
    # NGÒ - EXTERNAL UNIVERSITY SOURCE
    # ========================================================

    "SEC0018_NGO_TNAU": {

        "parent_document_id":
            "DOC0018",

        "source_id":
            "S05_TNAU",

        "crop_id":
            CROP_NGO,

        "crop_name":
            "Ngò / ngò rí",

        "section_mode":
            "FULL_DOCUMENT",

        "knowledge_scope":
            "scientific_external",

        "region":
            "INDIA_TAMIL_NADU",

        "local_applicability":
            "EXTERNAL_SUPPORTING",

        "evidence_role":
            "INDEPENDENT_EXTERNAL_AGRONOMY",

        "buckets": [
            B01,
            B02,
            B03,
            B04,
            B05,
        ],

        "bucket_markers": {

            B01: [
                [
                    "coriandrum sativum",
                    "coriander",
                ],
                [
                    "soil",
                    "season",
                    "harvest",
                ],
            ],

            B02: [
                [
                    "irrigation",
                ],
            ],

            B03: [
                [
                    "manuring",
                ],
                [
                    "fym",
                    "top dressing",
                ],
            ],

            B04: [
                [
                    "plant protection",
                ],
                [
                    "aphid",
                    "powdery mildew",
                    "wilt",
                ],
            ],

            B05: [
                [
                    "climate",
                ],
                [
                    "temperature",
                    "rainfed",
                    "drought",
                ],
            ],
        },

        "safety_notes": [
            (
                "This is an external agronomic source. "
                "Pesticide products or treatment rates from this "
                "source must NOT be interpreted as legal pesticide "
                "authorization in Vietnam."
            )
        ],
    },


    # ========================================================
    # CẢI CÚC - UF/IFAS
    # ========================================================

    "SEC0019_CAI_CUC_UF": {

        "parent_document_id":
            "DOC0019",

        "source_id":
            "S06_UF_IFAS",

        "crop_id":
            CROP_CAI_CUC,

        "crop_name":
            "Cải cúc / tần ô",

        "section_mode":
            "FULL_DOCUMENT",

        "knowledge_scope":
            "scientific_external",

        "region":
            "USA_FLORIDA",

        "local_applicability":
            "EXTERNAL_SUPPORTING",

        "evidence_role":
            "INDEPENDENT_EXTERNAL_AGRONOMY",

        # UF/IFAS supports crop profile, water/soil moisture
        # and weather/growing-condition knowledge.
        #
        # It is intentionally NOT assigned:
        # B03 = Nutrition
        # B04 = Pest & Disease
        "buckets": [
            B01,
            B02,
            B05,
        ],

        "bucket_markers": {

            B01: [
                [
                    "glebionis coronaria",
                    "tong hao",
                ],
                [
                    "harvested 40 to 45 days",
                    "how to grow tong hao",
                    "annual leafy herb",
                ],
            ],

            B02: [
                [
                    "damp but well-drained soil",
                    "well-drained soil",
                ],
            ],

            B05: [
                [
                    "optimum growth temperature",
                ],
                [
                    "hot temperatures",
                    "cool weather",
                    "spring and fall",
                ],
            ],
        },

        "safety_notes": [
            (
                "UF/IFAS is used as external scientific supporting "
                "evidence. Florida-specific management must not "
                "be blindly transferred to Vietnam."
            ),
            (
                "This source is intentionally NOT assigned B03 "
                "because specific UF/IFAS nutrient recommendations "
                "for Tong Hao are not available."
            ),
        ],
    },


    # ========================================================
    # CẢI CÚC - VIETNAM NATIONAL EXTENSION PDF
    # ========================================================

    "SEC0020_CAI_CUC_KN": {

        "parent_document_id":
            "DOC0020",

        "source_id":
            "S02_EXTENSION",

        "crop_id":
            CROP_CAI_CUC,

        "crop_name":
            "Cải cúc / tần ô",

        "section_mode":
            "EXTRACT_CAI_CUC_SECTION",

        "knowledge_scope":
            "crop_specific",

        "region":
            "VIETNAM",

        "local_applicability":
            "VIETNAM_GENERAL",

        "evidence_role":
            "PRIMARY_VIETNAM_EXTENSION_PARAMETER",

        # This PDF section contains economic/technical
        # production parameters.
        #
        # It does NOT substantively support B02/B04/B05.
        "buckets": [
            B01,
            B03,
        ],

        "bucket_markers": {

            B01: [
                [
                    "cải cúc",
                ],
                [
                    "hạt giống",
                    "thời gian triển khai",
                ],
            ],

            B03: [
                [
                    "phân đạm",
                    "đạm nguyên chất",
                ],
                [
                    "phân lân",
                    "lân nguyên chất",
                ],
                [
                    "phân kali",
                    "kali nguyên chất",
                ],
                [
                    "phân hữu cơ",
                ],
            ],
        },

        "safety_notes": [
            (
                "The monetary/item entry for pesticide in this "
                "economic-technical norm is NOT evidence that a "
                "specific pesticide is legally permitted."
            ),
            (
                "This section is not used as evidence for B02, "
                "B04 or B05 because those topics are not "
                "substantively described."
            ),
        ],
    },


    # ========================================================
    # CẢI CÚC - OMAFRA PEST & DISEASE
    # ========================================================

    "SEC0021_CAI_CUC_OMAFRA": {

        "parent_document_id":
            "DOC0021",

        "source_id":
            "S08_OMAFRA",

        "crop_id":
            CROP_CAI_CUC,

        "crop_name":
            "Cải cúc / tần ô",

        "section_mode":
            "FULL_DOCUMENT",

        "knowledge_scope":
            "scientific_external",

        "region":
            "CANADA_ONTARIO",

        "local_applicability":
            "EXTERNAL_SUPPORTING",

        "evidence_role":
            "INDEPENDENT_EXTERNAL_PEST_EVIDENCE",

        # OMAFRA was added specifically to fill
        # Cải cúc × B04_PEST_DISEASE.
        #
        # Do not use it to inflate other coverage cells.
        "buckets": [
            B04,
        ],

        "bucket_markers": {

            B04: [

                # Confirm correct crop.
                [
                    "chrysanthemum coronarium",
                    "edible chrysanthemum",
                    "tong hao",
                ],

                # Confirm insect pest evidence.
                [
                    "aphid",
                    "aphids",
                ],

                # Confirm disease evidence.
                [
                    "powdery mildew",
                ],

                # Require at least one additional pest group.
                [
                    "whitefly",
                    "whiteflies",
                    "mites",
                    "leafminers",
                    "leaf miners",
                    "japanese beetle",
                ],
            ],
        },

        "safety_notes": [
            (
                "OMAFRA is an external supporting source for "
                "pest and disease evidence only."
            ),
            (
                "Pesticide products, registrations or control "
                "recommendations from Ontario must NOT be treated "
                "as legal pesticide authorization in Vietnam."
            ),
            (
                "Current Vietnamese pesticide legality must come "
                "only from the separate B06 legal consolidation "
                "pipeline."
            ),
        ],
    },
}


# ============================================================
# IO
# ============================================================

def load_json(path: Path) -> dict:

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


def save_text(
    path: Path,
    text: str,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_search_text(
    text: str,
) -> str:

    value = unicodedata.normalize(
        "NFC",
        text or "",
    )

    value = value.casefold()

    value = value.replace(
        "\u00a0",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def contains_any(
    searchable_text: str,
    markers: list,
) -> bool:

    for marker in markers:

        marker_normalized = (
            normalize_search_text(
                marker
            )
        )

        if (
            marker_normalized
            in searchable_text
        ):

            return True

    return False


def sha256_text(
    text: str,
) -> str:

    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# LOAD PARENT
# ============================================================

def load_parent_document(
    document_id: str,
) -> tuple[dict, str]:

    registry_path = (
        DOCUMENT_DIR
        / f"{document_id}.json"
    )

    if not registry_path.exists():

        raise RuntimeError(
            f"{document_id}: registry file not found."
        )

    document = load_json(
        registry_path
    )

    if (
        document.get(
            "extraction_status"
        )
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: extraction is not SUCCESS."
        )

    if (
        document.get(
            "normalization_status"
        )
        != "SUCCESS"
    ):

        raise RuntimeError(
            f"{document_id}: normalization is not SUCCESS."
        )

    normalized_path_value = (
        document.get(
            "normalized_path"
        )
    )

    if not normalized_path_value:

        raise RuntimeError(
            f"{document_id}: normalized_path missing."
        )

    normalized_path = Path(
        normalized_path_value
    )

    if not normalized_path.exists():

        raise RuntimeError(
            f"{document_id}: normalized file not found."
        )

    text = normalized_path.read_text(
        encoding="utf-8"
    )

    return (
        document,
        text,
    )


# ============================================================
# DOC0020 SECTION SPLITTER
# ============================================================

def extract_cai_cuc_section(
    text: str,
) -> str:
    """
    Extract only the Cải cúc section from DOC0020.

    The parent PDF contains many different agricultural models.
    It must never be treated as one Cải cúc document.
    """

    text_lower = (
        text.casefold()
    )

    crop_positions = []

    for marker in [
        "rau cải cúc",
        "cải cúc",
    ]:

        position = (
            text_lower.find(
                marker.casefold()
            )
        )

        if position >= 0:

            crop_positions.append(
                position
            )

    if not crop_positions:

        raise RuntimeError(
            "DOC0020: cannot locate CẢI CÚC section."
        )

    crop_position = min(
        crop_positions
    )

    # ========================================================
    # Find section XIII before the crop title
    # ========================================================

    search_start = max(
        0,
        crop_position - 500,
    )

    prefix = (
        text_lower[
            search_start:
            crop_position
        ]
    )

    relative_xiii = max(
        prefix.rfind(
            "xiii."
        ),
        prefix.rfind(
            "xiii "
        ),
        prefix.rfind(
            "xiii\n"
        ),
    )

    if relative_xiii >= 0:

        section_start = (
            search_start
            + relative_xiii
        )

    else:

        section_start = (
            crop_position
        )

    # ========================================================
    # Find section XIV after Cải cúc
    # ========================================================

    end_candidates = []

    for marker in [
        "\nxiv.",
        "\nxiv ",
        " xiv.",
    ]:

        position = (
            text_lower.find(
                marker,
                crop_position + 1,
            )
        )

        if position >= 0:

            end_candidates.append(
                position
            )

    if end_candidates:

        section_end = min(
            end_candidates
        )

    else:

        raise RuntimeError(
            "DOC0020: start of section XIV not found; "
            "refusing unsafe section extraction."
        )

    result = (
        text[
            section_start:
            section_end
        ].strip()
    )

    if len(result) < 300:

        raise RuntimeError(
            "DOC0020: extracted Cải cúc section "
            "is unexpectedly short."
        )

    return result


# ============================================================
# GET SECTION TEXT
# ============================================================

def get_section_text(
    config: dict,
    parent_text: str,
) -> str:

    mode = (
        config[
            "section_mode"
        ]
    )

    if (
        mode
        == "FULL_DOCUMENT"
    ):

        return (
            parent_text.strip()
        )

    if (
        mode
        == "EXTRACT_CAI_CUC_SECTION"
    ):

        return (
            extract_cai_cuc_section(
                parent_text
            )
        )

    raise RuntimeError(
        f"Unknown section mode: {mode}"
    )


# ============================================================
# BUCKET EVIDENCE AUDIT
# ============================================================

def audit_bucket_markers(
    text: str,
    bucket_markers: dict,
):

    searchable = (
        normalize_search_text(
            text
        )
    )

    bucket_results = {}

    all_pass = True

    for bucket, groups in (
        bucket_markers.items()
    ):

        group_results = []

        bucket_pass = True

        for group in groups:

            passed = (
                contains_any(
                    searchable,
                    group,
                )
            )

            matched = []

            if passed:

                for marker in group:

                    if contains_any(
                        searchable,
                        [marker],
                    ):

                        matched.append(
                            marker
                        )

            group_results.append({

                "alternatives":
                    group,

                "passed":
                    passed,

                "matched":
                    matched,
            })

            if not passed:

                bucket_pass = False

        bucket_results[
            bucket
        ] = {

            "passed":
                bucket_pass,

            "groups":
                group_results,
        }

        if not bucket_pass:

            all_pass = False

    return (
        all_pass,
        bucket_results,
    )


# ============================================================
# PROCESS ONE TARGET
# ============================================================

def process_target(
    section_id: str,
    config: dict,
) -> dict:

    document_id = (
        config[
            "parent_document_id"
        ]
    )

    (
        parent_document,
        parent_text,
    ) = load_parent_document(
        document_id
    )

    # ========================================================
    # SOURCE MUST MATCH
    # ========================================================

    actual_source = (
        parent_document.get(
            "source_id"
        )
    )

    expected_source = (
        config[
            "source_id"
        ]
    )

    if (
        actual_source
        != expected_source
    ):

        raise RuntimeError(
            f"{section_id}: source mismatch. "
            f"Expected {expected_source}, "
            f"got {actual_source}."
        )

    # ========================================================
    # GET SECTION
    # ========================================================

    section_text = (
        get_section_text(
            config,
            parent_text,
        )
    )

    # ========================================================
    # CONTENT AUDIT
    # ========================================================

    (
        content_pass,
        bucket_evidence,
    ) = audit_bucket_markers(
        section_text,
        config[
            "bucket_markers"
        ],
    )

    # ========================================================
    # STATUS
    # ========================================================

    if content_pass:

        evidence_status = (
            "ACCEPTED_SECTION"
        )

        coverage_eligible = (
            True
        )

    else:

        evidence_status = (
            "REVIEW_REQUIRED"
        )

        coverage_eligible = (
            False
        )

    # ========================================================
    # PATHS
    # ========================================================

    text_path = (
        SECTION_TEXT_DIR
        / f"{section_id}.txt"
    )

    registry_path = (
        SECTION_REGISTRY_DIR
        / f"{section_id}.json"
    )

    save_text(
        text_path,
        section_text,
    )

    record = {

        "section_id":
            section_id,

        "parent_document_id":
            document_id,

        "source_id":
            expected_source,

        "source_url":
            parent_document.get(
                "url"
            ),

        "crop_entities": [
            config[
                "crop_id"
            ]
        ],

        "crop_name":
            config[
                "crop_name"
            ],

        "buckets":
            config[
                "buckets"
            ],

        "knowledge_scope":
            config[
                "knowledge_scope"
            ],

        "region":
            config[
                "region"
            ],

        "local_applicability":
            config[
                "local_applicability"
            ],

        "evidence_role":
            config[
                "evidence_role"
            ],

        "section_mode":
            config[
                "section_mode"
            ],

        "evidence_status":
            evidence_status,

        "coverage_eligible":
            coverage_eligible,

        "section_path":
            str(
                text_path
            ),

        "section_char_count":
            len(
                section_text
            ),

        "section_checksum":
            sha256_text(
                section_text
            ),

        "bucket_evidence":
            bucket_evidence,

        "safety_notes":
            config.get(
                "safety_notes"
            )
            or [],

        # None of these agronomy sections may authorize
        # pesticide legality.
        "legal_authorization_source":
            False,

        "rag_stage":
            (
                "READY_FOR_CHUNKING"
                if coverage_eligible
                else "REVIEW_REQUIRED"
            ),
    }

    save_json(
        registry_path,
        record,
    )

    return record


# ============================================================
# TARGET MATRIX
# ============================================================

def build_target_matrix(
    records: list,
):

    crops = [
        (
            CROP_NGO,
            "Ngò / ngò rí",
        ),
        (
            CROP_CAI_CUC,
            "Cải cúc / tần ô",
        ),
    ]

    buckets = [
        B01,
        B02,
        B03,
        B04,
        B05,
    ]

    result = {}

    for crop_id, crop_name in crops:

        result[
            crop_id
        ] = {

            "crop_name":
                crop_name,

            "buckets":
                {},
        }

        for bucket in buckets:

            evidence = []

            sources = []

            for record in records:

                if not record.get(
                    "coverage_eligible"
                ):
                    continue

                if (
                    crop_id
                    not in (
                        record.get(
                            "crop_entities"
                        )
                        or []
                    )
                ):
                    continue

                if (
                    bucket
                    not in (
                        record.get(
                            "buckets"
                        )
                        or []
                    )
                ):
                    continue

                evidence.append(
                    record[
                        "section_id"
                    ]
                )

                sources.append(
                    record[
                        "source_id"
                    ]
                )

            unique_sources = sorted(
                set(
                    sources
                )
            )

            if len(
                unique_sources
            ) >= 2:

                status = (
                    "R2+"
                )

            elif evidence:

                status = (
                    "R1"
                )

            else:

                status = (
                    "--"
                )

            result[
                crop_id
            ][
                "buckets"
            ][
                bucket
            ] = {

                "status":
                    status,

                "evidence":
                    sorted(
                        evidence
                    ),

                "sources":
                    unique_sources,
            }

    return result


# ============================================================
# PRINT MATRIX
# ============================================================

def print_matrix(
    matrix: dict,
):

    short_names = {
        B01: "B01",
        B02: "B02",
        B03: "B03",
        B04: "B04",
        B05: "B05",
    }

    buckets = [
        B01,
        B02,
        B03,
        B04,
        B05,
    ]

    print()
    print("=" * 78)
    print(
        "TARGETED GAP COVERAGE AFTER SECTION PROCESSING"
    )
    print("=" * 78)

    print(
        f"{'Crop':<22}"
        + "".join(
            f"{short_names[b]:>10}"
            for b in buckets
        )
    )

    print("-" * 78)

    for crop_id in [
        CROP_NGO,
        CROP_CAI_CUC,
    ]:

        crop_info = (
            matrix[
                crop_id
            ]
        )

        print(
            f"{crop_info['crop_name']:<22}"
            + "".join(
                f"{crop_info['buckets'][b]['status']:>10}"
                for b in buckets
            )
        )


# ============================================================
# MAIN
# ============================================================

def main():

    SECTION_TEXT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SECTION_REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 78)
    print(
        "AGRI RAG - TARGETED GAP SECTION PROCESSING"
    )
    print("=" * 78)

    print(
        f"Targets: {len(TARGETS)}"
    )

    records = []

    failed = []

    for index, (
        section_id,
        config,
    ) in enumerate(
        TARGETS.items(),
        start=1,
    ):

        print()
        print("-" * 78)

        print(
            f"[{index}/{len(TARGETS)}] "
            f"{section_id}"
        )

        try:

            record = (
                process_target(
                    section_id,
                    config,
                )
            )

            records.append(
                record
            )

            print(
                f"Parent             : "
                f"{record['parent_document_id']}"
            )

            print(
                f"Crop               : "
                f"{record['crop_name']}"
            )

            print(
                f"Source             : "
                f"{record['source_id']}"
            )

            print(
                f"Evidence role      : "
                f"{record['evidence_role']}"
            )

            print(
                f"Section mode       : "
                f"{record['section_mode']}"
            )

            print(
                f"Characters         : "
                f"{record['section_char_count']}"
            )

            print(
                f"Buckets            : "
                f"{record['buckets']}"
            )

            print(
                f"Evidence status    : "
                f"{record['evidence_status']}"
            )

            print(
                f"Coverage eligible  : "
                f"{record['coverage_eligible']}"
            )

            failed_buckets = [

                bucket

                for bucket, audit
                in (
                    record[
                        "bucket_evidence"
                    ].items()
                )

                if not audit[
                    "passed"
                ]
            ]

            print(
                f"Failed bucket audit: "
                f"{failed_buckets}"
            )

            print(
                f"Output             : "
                f"{record['section_path']}"
            )

        except Exception as exc:

            failed.append({

                "section_id":
                    section_id,

                "error":
                    str(exc),
            })

            print(
                f"[FAILED] {exc}"
            )

    # ========================================================
    # MATRIX
    # ========================================================

    matrix = build_target_matrix(
        records
    )

    print_matrix(
        matrix
    )

    # ========================================================
    # REMAINING GAPS
    # ========================================================

    missing = []

    for crop_id, crop_info in (
        matrix.items()
    ):

        for bucket, info in (
            crop_info[
                "buckets"
            ].items()
        ):

            if (
                info[
                    "status"
                ]
                == "--"
            ):

                missing.append({

                    "crop_id":
                        crop_id,

                    "crop_name":
                        crop_info[
                            "crop_name"
                        ],

                    "bucket":
                        bucket,
                })

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "processed":
            len(
                records
            ),

        "failed":
            len(
                failed
            ),

        "accepted_sections":
            sum(
                1
                for record in records
                if (
                    record[
                        "coverage_eligible"
                    ]
                )
            ),

        "review_sections":
            sum(
                1
                for record in records
                if not (
                    record[
                        "coverage_eligible"
                    ]
                )
            ),

        "target_matrix":
            matrix,

        "remaining_core_gaps":
            missing,

        "failures":
            failed,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print()
    print("=" * 78)
    print(
        "TARGETED GAP PROCESSING SUMMARY"
    )
    print("=" * 78)

    print(
        f"Processed sections  : "
        f"{summary['processed']}"
    )

    print(
        f"Accepted sections   : "
        f"{summary['accepted_sections']}"
    )

    print(
        f"Review sections     : "
        f"{summary['review_sections']}"
    )

    print(
        f"Failed processing   : "
        f"{summary['failed']}"
    )

    print(
        f"Remaining core gaps : "
        f"{len(missing)}"
    )

    if missing:

        print()
        print(
            "REMAINING GAPS"
        )

        for gap in missing:

            print(
                f"- "
                f"{gap['crop_name']} "
                f"→ {gap['bucket']}"
            )

    else:

        print()
        print(
            "No remaining targeted core agronomy gaps."
        )

    print()
    print(
        f"Summary             : "
        f"{SUMMARY_FILE}"
    )

    print()
    print(
        "NOTE: These are evidence sections, "
        "not final retrieval chunks."
    )

    print(
        "B06 pesticide legality remains isolated "
        "from these agronomy sections."
    )


if __name__ == "__main__":
    main()
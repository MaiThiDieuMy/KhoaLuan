import csv
import json
import re
from datetime import datetime
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


# ============================================================
# PATHS
# ============================================================

DOCUMENT_DIR = Path(
    "data/agri_rag/registry/documents"
)

DOWNLOAD_REGISTRY_FILE = Path(
    "data/agri_rag/registry/download_registry.csv"
)

SOURCE_CONFIG_FILE = Path(
    "src/agri_rag/config/approved_sources.yaml"
)

CROP_CONFIG_FILE = Path(
    "src/agri_rag/config/crops.yaml"
)

LEGAL_REGISTRY_FILE = Path(
    "src/agri_rag/config/legal_registry.yaml"
)


# ============================================================
# BUCKET KEYWORDS
#
# B06 và B08 cố ý KHÔNG nằm ở đây.
#
# B06:
#   chỉ legal document thực sự mới được gắn.
#
# B08:
#   dựa source/seed/document family/local context,
#   không dựa một địa danh xuất hiện ngẫu nhiên.
# ============================================================

BUCKET_KEYWORDS = {

    "B01_CROP_PROFILE": [
        "thời vụ",
        "giống",
        "sinh trưởng",
        "phát triển",
        "gieo trồng",
        "gieo hạt",
        "thu hoạch",
        "chu kỳ",
    ],

    "B02_WATER": [
        "tưới nước",
        "nhu cầu nước",
        "độ ẩm",
        "thoát nước",
        "ngập úng",
        "khô hạn",
        "tưới",
    ],

    "B03_NUTRITION": [
        "phân bón",
        "bón phân",
        "bón lót",
        "bón thúc",
        "dinh dưỡng",
        "phân hữu cơ",
    ],

    "B04_PEST_DISEASE": [
        "sâu bệnh",
        "sâu hại",
        "bệnh hại",
        "dịch hại",
        "phòng trừ",
        "phòng bệnh",
        "ipm",
    ],

    "B05_WEATHER_CARE": [
        "mưa lớn",
        "nắng nóng",
        "gió mạnh",
        "rét",
        "thời tiết",
        "khô hạn",
        "ngập úng",
        "mưa",
    ],

    "B07_GAP_SAFETY": [
        "vietgap",
        "an toàn thực phẩm",
        "truy xuất nguồn gốc",
        "rau an toàn",
        "an toàn sản xuất",
    ],
}


# ============================================================
# LEGAL ROLE -> DOCUMENT FAMILY
# ============================================================

LEGAL_REGULATION_ROLES = {
    "BASE_INSTRUMENT_NOTICE",
    "AMENDMENT_INSTRUMENT_NOTICE",
    "BASE_INSTRUMENT_PDF",
    "AMENDMENT_INSTRUMENT_PDF",
}


LEGAL_ATTACHMENT_ROLES = {
    "BASE_ALLOWED_LIST",
    "BASE_BANNED_LIST",
    "AMENDMENT_APPENDICES",
}


# ============================================================
# BASIC IO
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

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return (
            yaml.safe_load(file)
            or {}
        )


def load_download_registry() -> dict:

    result = {}

    if not DOWNLOAD_REGISTRY_FILE.exists():
        return result

    with DOWNLOAD_REGISTRY_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            document_id = (
                row.get(
                    "document_id"
                )
                or ""
            ).strip()

            if document_id:

                result[
                    document_id
                ] = row

    return result


# ============================================================
# LEGAL REGISTRY INDEX
# ============================================================

def build_legal_document_index(
    legal_registry: dict,
) -> dict:

    result = {}

    roles = (
        legal_registry.get(
            "document_roles"
        )
        or {}
    )

    instruments = (
        legal_registry.get(
            "legal_instruments"
        )
        or {}
    )

    for document_id, role_info in (
        roles.items()
    ):

        instrument_key = (
            role_info.get(
                "legal_instrument"
            )
        )

        instrument = (
            instruments.get(
                instrument_key
            )
            or {}
        )

        result[
            document_id
        ] = {
            "instrument_key":
                instrument_key,

            "legal_role":
                role_info.get(
                    "legal_role"
                ),

            "instrument":
                instrument,
        }

    return result


# ============================================================
# DATE
# ============================================================

def parse_vietnamese_date(
    raw_date: str,
):

    if not raw_date:
        return None

    try:

        parsed = datetime.strptime(
            raw_date.strip(),
            "%d/%m/%Y",
        )

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except ValueError:

        return None


def detect_published_date(
    text: str,
):

    patterns = [
        (
            r"Ngày\s+đăng\s*:\s*"
            r"(\d{1,2}/\d{1,2}/\d{4})"
        ),

        (
            r"Ngày\s+cập\s+nhật\s*:\s*"
            r"(\d{1,2}/\d{1,2}/\d{4})"
        ),

        (
            r"Cập\s+nhật\s+lúc"
            r".{0,80}?"
            r"(\d{1,2}/\d{1,2}/\d{4})"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        result = (
            parse_vietnamese_date(
                match.group(1)
            )
        )

        if result:
            return result

    return None


def detect_published_date_from_raw_html(
    raw_path_value,
):

    if not raw_path_value:
        return None

    raw_path = Path(
        raw_path_value
    )

    if not raw_path.exists():
        return None

    if (
        raw_path.suffix.lower()
        != ".html"
    ):
        return None

    html = raw_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    # ========================================================
    # HTML metadata
    # ========================================================

    meta_candidates = [
        soup.find(
            "meta",
            attrs={
                "property":
                    "article:published_time"
            },
        ),

        soup.find(
            "meta",
            attrs={
                "name":
                    "date"
            },
        ),

        soup.find(
            "meta",
            attrs={
                "name":
                    "publish-date"
            },
        ),
    ]

    for meta in meta_candidates:

        if not meta:
            continue

        content = (
            meta.get(
                "content"
            )
            or ""
        ).strip()

        iso_match = re.search(
            r"(\d{4}-\d{2}-\d{2})",
            content,
        )

        if iso_match:

            return (
                iso_match.group(1)
            )

        vn_match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4})",
            content,
        )

        if vn_match:

            result = (
                parse_vietnamese_date(
                    vn_match.group(1)
                )
            )

            if result:
                return result

    # ========================================================
    # Fallback: whole HTML page
    # ========================================================

    page_text = soup.get_text(
        " ",
        strip=True,
    )

    return detect_published_date(
        page_text
    )


# ============================================================
# CROP DETECTION
# ============================================================

def phrase_exists(
    text: str,
    phrase: str,
) -> bool:

    text_cf = (
        text.casefold()
    )

    phrase_cf = (
        phrase.casefold()
    )

    pattern = (
        r"(?<!\w)"
        + re.escape(
            phrase_cf
        )
        + r"(?!\w)"
    )

    return bool(
        re.search(
            pattern,
            text_cf,
        )
    )


def detect_crops(
    text: str,
    crops_config: dict,
):

    detected = []

    for crop_id, crop_info in (
        crops_config.items()
    ):

        aliases = (
            crop_info.get(
                "aliases"
            )
            or []
        )

        for alias in aliases:

            if phrase_exists(
                text,
                alias,
            ):

                detected.append(
                    crop_id
                )

                break

    return sorted(
        set(
            detected
        )
    )


# ============================================================
# DOCUMENT FAMILY
# ============================================================

def detect_document_family(
    document_id: str,
    url: str,
    source_id: str,
    expected_bucket: str,
    title: str,
    legal_index: dict,
):
    """
    Ưu tiên explicit Legal Registry.

    Chỉ fallback heuristic nếu document không phải
    một document pháp lý đã đăng ký.
    """

    # ========================================================
    # 1. LEGAL REGISTRY
    # ========================================================

    legal_info = (
        legal_index.get(
            document_id
        )
    )

    if legal_info:

        role = (
            legal_info.get(
                "legal_role"
            )
        )

        if (
            role
            in LEGAL_REGULATION_ROLES
        ):

            return "regulation"

        if (
            role
            in LEGAL_ATTACHMENT_ROLES
        ):

            return (
                "regulatory_attachment"
            )

    # ========================================================
    # 2. FALLBACK
    # ========================================================

    url_lower = (
        url or ""
    ).casefold()

    title_lower = (
        title or ""
    ).casefold()

    # --------------------------------------------------------
    # Regulation HTML
    # --------------------------------------------------------

    if (
        "van-ban-chinh-sach"
        in url_lower
        or
        "thông tư"
        in title_lower
    ):

        return "regulation"

    # --------------------------------------------------------
    # Khuyến nông bulletin
    # --------------------------------------------------------

    if (
        source_id
        == "S02_EXTENSION"
        and
        "/data/documents/"
        in url_lower
    ):

        return (
            "extension_bulletin"
        )

    # --------------------------------------------------------
    # Khuyến nông article
    # --------------------------------------------------------

    if (
        source_id
        == "S02_EXTENSION"
    ):

        if (
            expected_bucket
            == "B08_LOCAL"
        ):

            return (
                "local_extension_article"
            )

        return "technical_guide"

    # --------------------------------------------------------
    # ASISOV
    # --------------------------------------------------------

    if (
        source_id
        == "S03_ASISOV"
    ):

        if (
            "/pages/bo-mon"
            in url_lower
        ):

            return (
                "institution_profile"
            )

        if (
            ".pdf"
            in url_lower
        ):

            return (
                "conference_proceedings"
            )

    # --------------------------------------------------------
    # Generic PPD PDF
    # --------------------------------------------------------

    if (
        source_id
        == "S01_PPD"
        and
        ".pdf"
        in url_lower
    ):

        return (
            "technical_document"
        )

    return "web_document"


# ============================================================
# BUCKETS
# ============================================================

def suggest_buckets(
    text: str,
    expected_bucket: str,
    document_family: str,
):
    """
    Legal documents:
        B06 only.

    Technical documents:
        expected bucket + keyword suggestions.
    """

    # ========================================================
    # LEGAL DOCUMENT
    # ========================================================

    if document_family in {
        "regulation",
        "regulatory_attachment",
    }:

        return [
            "B06_PESTICIDE_LEGAL"
        ]

    suggested = set()

    # ========================================================
    # Seed expectation
    # ========================================================

    if expected_bucket:

        suggested.add(
            expected_bucket
        )

    text_lower = (
        text.casefold()
    )

    # ========================================================
    # Keyword suggestions
    # ========================================================

    for bucket, keywords in (
        BUCKET_KEYWORDS.items()
    ):

        for keyword in keywords:

            if (
                keyword.casefold()
                in text_lower
            ):

                suggested.add(
                    bucket
                )

                break

    # ========================================================
    # Local families
    # ========================================================

    if document_family in {
        "local_extension_article",
        "institution_profile",
        "conference_proceedings",
    }:

        suggested.add(
            "B08_LOCAL"
        )

    return sorted(
        suggested
    )


# ============================================================
# REGION
# ============================================================

def detect_region(
    text: str,
    source_info: dict,
    document_family: str,
    legal_info,
):

    # ========================================================
    # Legal registry is authoritative for jurisdiction
    # ========================================================

    if legal_info:

        jurisdiction = (
            legal_info
            .get(
                "instrument",
                {}
            )
            .get(
                "jurisdiction"
            )
        )

        if jurisdiction:
            return jurisdiction

    text_lower = (
        text.casefold()
    )

    # ========================================================
    # Local article
    # ========================================================

    if (
        document_family
        == "local_extension_article"
    ):

        if (
            "bình định"
            in text_lower
        ):

            return (
                "BINH_DINH_LEGACY"
            )

        if (
            "gia lai"
            in text_lower
        ):

            return "GIA_LAI"

    # ========================================================
    # Conference
    # ========================================================

    if (
        document_family
        == "conference_proceedings"
    ):

        if (
            "nam trung bộ"
            in text_lower
            or
            "duyên hải nam trung bộ"
            in text_lower
        ):

            return (
                "SOUTH_CENTRAL_COAST"
            )

    # ========================================================
    # National bulletin
    # ========================================================

    if (
        document_family
        == "extension_bulletin"
    ):

        return "VIETNAM"

    # ========================================================
    # Legal fallback
    # ========================================================

    if document_family in {
        "regulation",
        "regulatory_attachment",
    }:

        return "VIETNAM"

    # ========================================================
    # Source geography
    # ========================================================

    geography = (
        source_info.get(
            "geography"
        )
        or []
    )

    if len(geography) == 1:

        return geography[0]

    return None


# ============================================================
# LOCAL APPLICABILITY
# ============================================================

def determine_local_applicability(
    region,
):

    if (
        region
        == "BINH_DINH_LEGACY"
    ):

        return "LOCAL_DIRECT"

    if (
        region
        == "GIA_LAI"
    ):

        return "LOCAL_DIRECT"

    if (
        region
        == "SOUTH_CENTRAL_COAST"
    ):

        return (
            "SOUTH_CENTRAL_REGION"
        )

    if (
        region
        == "VIETNAM"
    ):

        return "VIETNAM_GENERAL"

    if (
        region
        == "GLOBAL"
    ):

        return (
            "GENERAL_SCIENTIFIC"
        )

    return None


# ============================================================
# KNOWLEDGE SCOPE
# ============================================================

def determine_knowledge_scope(
    document_family: str,
    crop_entities: list,
    text: str,
):

    if document_family in {
        "regulation",
        "regulatory_attachment",
    }:

        return "regulatory"

    if (
        document_family
        == "institution_profile"
    ):

        return "local_context"

    if (
        document_family
        == "conference_proceedings"
    ):

        return "local_context"

    if (
        document_family
        == "extension_bulletin"
    ):

        return "general_agronomy"

    if crop_entities:

        return "crop_specific"

    text_lower = (
        text.casefold()
    )

    group_terms = [
        "rau ăn lá",
        "rau màu",
        "cây rau",
        "các loại rau",
        "sản xuất rau",
        "rau vụ đông",
    ]

    if any(
        term in text_lower
        for term in group_terms
    ):

        return "crop_group"

    if (
        document_family
        == "local_extension_article"
    ):

        return "local_context"

    return "general_agronomy"


# ============================================================
# PUBLISHED DATE
# ============================================================

def resolve_published_date(
    document: dict,
    searchable_text: str,
    legal_info,
):

    # ========================================================
    # Legal document:
    # use verified instrument issue date
    # ========================================================

    if legal_info:

        legal_date = (
            legal_info
            .get(
                "instrument",
                {}
            )
            .get(
                "issued_date"
            )
        )

        if legal_date:

            return (
                legal_date,
                "LEGAL_REGISTRY",
            )

    # ========================================================
    # Extracted text
    # ========================================================

    detected = (
        detect_published_date(
            searchable_text
        )
    )

    if detected:

        return (
            detected,
            "CONTENT_LABEL",
        )

    # ========================================================
    # Raw HTML
    # ========================================================

    detected = (
        detect_published_date_from_raw_html(
            document.get(
                "raw_path"
            )
        )
    )

    if detected:

        return (
            detected,
            "RAW_HTML",
        )

    return (
        None,
        None,
    )


# ============================================================
# NOTES
# ============================================================

def build_metadata_notes(
    document_family: str,
    published_date,
    suggested_buckets: list,
    region,
    legal_info,
):

    notes = []

    if not suggested_buckets:

        notes.append(
            "NO_BUCKET_SUGGESTED"
        )

    if not region:

        notes.append(
            "REGION_UNRESOLVED"
        )

    if not published_date:

        notes.append(
            "PUBLISHED_DATE_NOT_RESOLVED"
        )

    if document_family in {
        "extension_bulletin",
        "conference_proceedings",
    }:

        notes.append(
            "MULTI_TOPIC_DOCUMENT_REQUIRES_SECTION_LEVEL_CHUNKING"
        )

    if (
        document_family
        == "institution_profile"
    ):

        notes.append(
            "SOURCE_EVIDENCE_NOT_PRIMARY_RAG_KNOWLEDGE"
        )

    if legal_info:

        notes.append(
            "LEGAL_METADATA_FROM_VERIFIED_REGISTRY"
        )

    return notes


# ============================================================
# INVALIDATE DOWNSTREAM QUALITY RESULT
# ============================================================

def invalidate_quality_result(
    document: dict,
):
    """
    Metadata được chạy lại thì kết quả Quality Gate cũ
    không còn được coi là current.

    Không xóa raw/extracted/normalized data.
    """

    document[
        "quality_status"
    ] = "PENDING_REVIEW"

    document[
        "quality_reasons"
    ] = []

    document[
        "rag_eligible"
    ] = False

    document[
        "buckets"
    ] = []

    document[
        "chunking_strategy"
    ] = None

    document[
        "quality_checked_at"
    ] = None


# ============================================================
# ENRICH ONE DOCUMENT
# ============================================================

def enrich_document(
    registry_path: Path,
    source_config: dict,
    crops_config: dict,
    download_registry: dict,
    legal_index: dict,
):

    document = load_json(
        registry_path
    )

    document_id = (
        document[
            "document_id"
        ]
    )

    # ========================================================
    # 1. Must have normalized text
    # ========================================================

    if (
        document.get(
            "normalization_status"
        )
        != "SUCCESS"
    ):

        document[
            "metadata_status"
        ] = "SKIPPED"

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id":
                document_id,

            "status":
                "SKIPPED",

            "reason":
                "NORMALIZATION_NOT_SUCCESS",
        }

    # ========================================================
    # 2. normalized_path
    # ========================================================

    normalized_path_value = (
        document.get(
            "normalized_path"
        )
    )

    if not normalized_path_value:

        document[
            "metadata_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "metadata_notes"
        ] = [
            "NORMALIZED_PATH_MISSING"
        ]

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "NORMALIZED_PATH_MISSING",
        }

    normalized_path = Path(
        normalized_path_value
    )

    if not normalized_path.exists():

        document[
            "metadata_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "metadata_notes"
        ] = [
            "NORMALIZED_FILE_NOT_FOUND"
        ]

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "NORMALIZED_FILE_NOT_FOUND",
        }

    text = normalized_path.read_text(
        encoding="utf-8"
    )

    title = (
        document.get(
            "title"
        )
        or ""
    )

    searchable_text = (
        title
        + "\n"
        + text
    )

    # ========================================================
    # 3. Source
    # ========================================================

    source_id = (
        document.get(
            "source_id"
        )
    )

    source_info = (
        source_config.get(
            source_id
        )
    )

    if not source_info:

        document[
            "metadata_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        document[
            "metadata_notes"
        ] = [
            "SOURCE_NOT_FOUND_IN_APPROVED_REGISTRY"
        ]

        save_json(
            registry_path,
            document,
        )

        return {
            "document_id":
                document_id,

            "status":
                "REVIEW_REQUIRED",

            "reason":
                "SOURCE_NOT_APPROVED",
        }

    # ========================================================
    # 4. Seed / download metadata
    # ========================================================

    download_row = (
        download_registry.get(
            document_id,
            {}
        )
    )

    expected_bucket = (
        download_row.get(
            "expected_bucket"
        )
        or ""
    ).strip()

    # ========================================================
    # 5. Legal registry metadata
    # ========================================================

    legal_info = (
        legal_index.get(
            document_id
        )
    )

    # ========================================================
    # 6. Family
    # ========================================================

    document_family = (
        detect_document_family(
            document_id,
            document.get(
                "url",
                "",
            ),
            source_id,
            expected_bucket,
            title,
            legal_index,
        )
    )

    # ========================================================
    # 7. Crops
    # ========================================================

    crop_entities = (
        detect_crops(
            searchable_text,
            crops_config,
        )
    )

    # ========================================================
    # 8. Buckets
    # ========================================================

    suggested_buckets = (
        suggest_buckets(
            searchable_text,
            expected_bucket,
            document_family,
        )
    )

    # ========================================================
    # 9. Region
    # ========================================================

    region = (
        detect_region(
            searchable_text,
            source_info,
            document_family,
            legal_info,
        )
    )

    local_applicability = (
        determine_local_applicability(
            region
        )
    )

    # ========================================================
    # 10. Date
    # ========================================================

    (
        published_date,
        published_date_source,
    ) = resolve_published_date(
        document,
        searchable_text,
        legal_info,
    )

    # ========================================================
    # 11. Scope
    # ========================================================

    knowledge_scope = (
        determine_knowledge_scope(
            document_family,
            crop_entities,
            searchable_text,
        )
    )

    # ========================================================
    # 12. Notes
    # ========================================================

    notes = build_metadata_notes(
        document_family,
        published_date,
        suggested_buckets,
        region,
        legal_info,
    )

    # ========================================================
    # 13. Write metadata
    # ========================================================

    document[
        "document_family"
    ] = document_family

    document[
        "published_date"
    ] = published_date

    document[
        "published_date_source"
    ] = published_date_source

    document[
        "crop_entities"
    ] = crop_entities

    document[
        "suggested_buckets"
    ] = suggested_buckets

    document[
        "knowledge_scope"
    ] = knowledge_scope

    document[
        "region"
    ] = region

    document[
        "source_credibility"
    ] = source_info.get(
        "credibility"
    )

    document[
        "local_applicability"
    ] = local_applicability

    document[
        "metadata_notes"
    ] = notes

    # ========================================================
    # 14. Legal hints
    #
    # Đây là metadata từ registry.
    # KHÔNG thay thế Legal Validation.
    # ========================================================

    if legal_info:

        document[
            "legal_registry_key"
        ] = legal_info.get(
            "instrument_key"
        )

        document[
            "legal_role_hint"
        ] = legal_info.get(
            "legal_role"
        )

        document[
            "legal_identifier_hint"
        ] = (
            legal_info
            .get(
                "instrument",
                {}
            )
            .get(
                "identifier"
            )
        )

    else:

        document[
            "legal_registry_key"
        ] = None

        document[
            "legal_role_hint"
        ] = None

        document[
            "legal_identifier_hint"
        ] = None

    # ========================================================
    # 15. Metadata validation
    # ========================================================

    critical_problem = (
        not suggested_buckets
        or
        not source_id
        or
        not source_info
    )

    if critical_problem:

        document[
            "metadata_status"
        ] = "REVIEW_REQUIRED"

        document[
            "quality_status"
        ] = "REVIEW_REQUIRED"

        status = (
            "REVIEW_REQUIRED"
        )

    else:

        document[
            "metadata_status"
        ] = "SUCCESS"

        # Metadata mới => Quality Gate cũ không còn current.
        invalidate_quality_result(
            document
        )

        status = "SUCCESS"

    save_json(
        registry_path,
        document,
    )

    return {
        "document_id":
            document_id,

        "status":
            status,

        "source_id":
            source_id,

        "document_family":
            document_family,

        "published_date":
            published_date,

        "published_date_source":
            published_date_source,

        "crop_entities":
            crop_entities,

        "suggested_buckets":
            suggested_buckets,

        "knowledge_scope":
            knowledge_scope,

        "region":
            region,

        "source_credibility":
            document.get(
                "source_credibility"
            ),

        "local_applicability":
            local_applicability,

        "legal_role_hint":
            document.get(
                "legal_role_hint"
            ),

        "legal_identifier_hint":
            document.get(
                "legal_identifier_hint"
            ),

        "notes":
            notes,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    source_config = load_yaml(
        SOURCE_CONFIG_FILE
    )

    crops_config = load_yaml(
        CROP_CONFIG_FILE
    )

    legal_registry = load_yaml(
        LEGAL_REGISTRY_FILE
    )

    legal_index = (
        build_legal_document_index(
            legal_registry
        )
    )

    download_registry = (
        load_download_registry()
    )

    registry_files = sorted(
        DOCUMENT_DIR.glob(
            "DOC*.json"
        )
    )

    success_count = 0
    skipped_count = 0
    review_count = 0
    failed_count = 0

    failed_items = []

    print()
    print("=" * 78)
    print("AGRI RAG - METADATA ENRICHMENT V3")
    print("=" * 78)

    print(
        f"Documents found: "
        f"{len(registry_files)}"
    )

    print(
        f"Legal registry documents: "
        f"{len(legal_index)}"
    )

    for index, registry_path in enumerate(
        registry_files,
        start=1,
    ):

        print()
        print("-" * 78)

        print(
            f"[{index}/{len(registry_files)}] "
            f"{registry_path.stem}"
        )

        try:

            result = enrich_document(
                registry_path,
                source_config,
                crops_config,
                download_registry,
                legal_index,
            )

            status = (
                result[
                    "status"
                ]
            )

            print(
                f"Status             : "
                f"{status}"
            )

            if (
                status
                == "SUCCESS"
            ):

                success_count += 1

                print(
                    f"Source             : "
                    f"{result['source_id']}"
                )

                print(
                    f"Family             : "
                    f"{result['document_family']}"
                )

                print(
                    f"Published date     : "
                    f"{result['published_date']}"
                )

                print(
                    f"Date source        : "
                    f"{result['published_date_source']}"
                )

                print(
                    f"Crops              : "
                    f"{result['crop_entities']}"
                )

                print(
                    f"Suggested buckets  : "
                    f"{result['suggested_buckets']}"
                )

                print(
                    f"Knowledge scope    : "
                    f"{result['knowledge_scope']}"
                )

                print(
                    f"Region             : "
                    f"{result['region']}"
                )

                print(
                    f"Credibility        : "
                    f"{result['source_credibility']}"
                )

                print(
                    f"Local applicability: "
                    f"{result['local_applicability']}"
                )

                print(
                    f"Legal identifier   : "
                    f"{result['legal_identifier_hint']}"
                )

                print(
                    f"Legal role         : "
                    f"{result['legal_role_hint']}"
                )

                print(
                    f"Notes              : "
                    f"{result['notes']}"
                )

            elif (
                status
                == "SKIPPED"
            ):

                skipped_count += 1

                print(
                    f"Reason             : "
                    f"{result['reason']}"
                )

            elif (
                status
                == "REVIEW_REQUIRED"
            ):

                review_count += 1

                print(
                    f"Reason             : "
                    f"{result.get('reason')}"
                )

        except Exception as exc:

            failed_count += 1

            failed_items.append({
                "document_id":
                    registry_path.stem,

                "error":
                    str(exc),
            })

            print(
                f"[FAILED] {exc}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 78)
    print("METADATA ENRICHMENT SUMMARY")
    print("=" * 78)

    print(
        f"Total documents : "
        f"{len(registry_files)}"
    )

    print(
        f"SUCCESS         : "
        f"{success_count}"
    )

    print(
        f"SKIPPED         : "
        f"{skipped_count}"
    )

    print(
        f"REVIEW_REQUIRED : "
        f"{review_count}"
    )

    print(
        f"FAILED          : "
        f"{failed_count}"
    )

    if failed_items:

        print()
        print("FAILED ITEMS")
        print("-" * 78)

        print(
            json.dumps(
                failed_items,
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
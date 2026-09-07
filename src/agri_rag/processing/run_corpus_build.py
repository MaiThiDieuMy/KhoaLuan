import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

ROOT = Path("data/agri_rag")

REGISTRY_DIR = ROOT / "registry"
DOCUMENT_REGISTRY_DIR = REGISTRY_DIR / "documents"
SECTION_REGISTRY_DIR = REGISTRY_DIR / "sections"

ACCEPTED_MANIFEST = (
    REGISTRY_DIR
    / "accepted_manifest.jsonl"
)

CORPUS_DIR = (
    ROOT
    / "corpus"
)

CHUNKS_FILE = (
    CORPUS_DIR
    / "chunks.jsonl"
)

CORPUS_MANIFEST_FILE = (
    CORPUS_DIR
    / "corpus_manifest.json"
)


# ============================================================
# CHUNKING CONFIG
#
# ~1200-1600 characters normally gives a useful retrieval unit
# without creating extremely small fragments.
# ============================================================

TARGET_CHARS = 1400
MAX_CHARS = 1800
OVERLAP_CHARS = 220
MIN_CHUNK_CHARS = 180


# ============================================================
# KNOWLEDGE BUCKETS
# ============================================================

LEGAL_BUCKET = (
    "B06_PESTICIDE_LEGAL"
)

ALLOWED_RAG_BUCKETS = {
    "B01_CROP_PROFILE",
    "B02_WATER",
    "B03_NUTRITION",
    "B04_PEST_DISEASE",
    "B05_WEATHER_CARE",
    "B07_GAP_SAFETY",
    "B08_LOCAL",
}


# ============================================================
# TARGET CROPS
# ============================================================

TARGET_CROPS = {
    "cai_xanh": [
        "cai_xanh",
        "cải xanh",
        "cải bẹ xanh",
    ],

    "ngo": [
        "ngo",
        "ngò",
        "ngò rí",
        "rau mùi",
    ],

    "cai_cuc": [
        "cai_cuc",
        "cải cúc",
        "tần ô",
        "tong hao",
        "edible chrysanthemum",
    ],

    "rau_muong": [
        "rau_muong",
        "rau muống",
        "water spinach",
    ],

    "xa_lach": [
        "xa_lach",
        "xà lách",
        "lettuce",
    ],
}


# ============================================================
# BUCKET KEYWORDS
#
# These do NOT create new agronomic facts.
#
# They only assign a parent-approved chunk to one or more
# retrieval buckets based on deterministic text markers.
#
# A bucket is never assigned if it was not already allowed by
# the parent document / validated section metadata.
# ============================================================

BUCKET_KEYWORDS = {
    "B01_CROP_PROFILE": [
        "giống",
        "thời vụ",
        "gieo",
        "gieo trồng",
        "trồng",
        "mật độ",
        "khoảng cách",
        "thu hoạch",
        "sinh trưởng",
        "phát triển",
        "nảy mầm",
        "đất",
        "ph đất",
        "độ ph",
        "soil",
        "variety",
        "cultivar",
        "sowing",
        "planting",
        "harvest",
        "growth",
    ],

    "B02_WATER": [
        "tưới",
        "nước",
        "độ ẩm",
        "ẩm độ đất",
        "thiếu nước",
        "úng",
        "ngập",
        "thoát nước",
        "irrigation",
        "water",
        "moisture",
        "drainage",
        "watering",
    ],

    "B03_NUTRITION": [
        "phân bón",
        "bón phân",
        "bón lót",
        "bón thúc",
        "đạm",
        "lân",
        "kali",
        "npk",
        "dinh dưỡng",
        "fertilizer",
        "fertiliser",
        "nitrogen",
        "phosphorus",
        "potassium",
        "nutrient",
    ],

    "B04_PEST_DISEASE": [
        "sâu bệnh",
        "sâu ",
        "bệnh ",
        "rệp",
        "bọ trĩ",
        "bọ nhảy",
        "nhện",
        "nấm",
        "vi khuẩn",
        "virus",
        "thán thư",
        "sương mai",
        "mốc",
        "thối",
        "héo",
        "pest",
        "disease",
        "insect",
        "fungus",
        "fungal",
        "pathogen",
        "mildew",
        "aphid",
    ],

    "B05_WEATHER_CARE": [
        "thời tiết",
        "nhiệt độ",
        "mưa",
        "nắng",
        "gió",
        "độ ẩm không khí",
        "rét",
        "nóng",
        "sương",
        "weather",
        "temperature",
        "rain",
        "rainfall",
        "humidity",
        "wind",
        "frost",
        "heat",
        "sunlight",
    ],

    "B07_GAP_SAFETY": [
        "vietgap",
        "gap",
        "an toàn thực phẩm",
        "an toàn sản xuất",
        "vệ sinh",
        "truy xuất",
        "ghi chép",
        "safety",
        "food safety",
        "traceability",
        "good agricultural practice",
    ],

    "B08_LOCAL": [
        "bình định",
        "gia lai",
        "địa phương",
        "hợp tác xã",
        "htx",
        "miền trung",
        "nam trung bộ",
        "south central coast",
    ],
}


# ============================================================
# BASIC IO
# ============================================================

def load_json(path: Path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_json(
    path: Path,
    data,
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


def load_jsonl(path: Path):

    rows = []

    if not path.exists():
        return rows

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            rows.append(
                json.loads(line)
            )

    return rows


def write_jsonl(
    path: Path,
    rows,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for row in rows:

            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
            )

            file.write("\n")


# ============================================================
# TEXT
# ============================================================

def normalize_text(text):

    text = unicodedata.normalize(
        "NFC",
        text or "",
    )

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        lines.append(line)

    text = "\n".join(lines)

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def fold_text(text):

    text = normalize_text(
        text
    ).casefold()

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    return text


def checksum_text(text):

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================
# PATH HANDLING
# ============================================================

def resolve_data_path(
    value,
):

    if not value:
        return None

    path = Path(
        str(value)
    )

    if path.exists():
        return path

    # Helpful if metadata was produced with Windows separators.
    normalized = Path(
        str(value).replace(
            "\\",
            "/",
        )
    )

    if normalized.exists():
        return normalized

    return path


# ============================================================
# METADATA HELPERS
# ============================================================

def listify(value):

    if value is None:
        return []

    if isinstance(
        value,
        list,
    ):
        return value

    if isinstance(
        value,
        (
            tuple,
            set,
        ),
    ):
        return list(value)

    return [value]


def normalize_bucket_list(value):

    result = []

    for item in listify(value):

        if isinstance(
            item,
            str,
        ):

            bucket = item.strip()

            if bucket:
                result.append(bucket)

    return sorted(
        set(result)
    )


def recursively_collect_strings(
    value,
):

    result = []

    if isinstance(
        value,
        str,
    ):

        result.append(value)

    elif isinstance(
        value,
        dict,
    ):

        for item in value.values():

            result.extend(
                recursively_collect_strings(
                    item
                )
            )

    elif isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        for item in value:

            result.extend(
                recursively_collect_strings(
                    item
                )
            )

    return result


def derive_crop_ids(
    crop_entities,
    text="",
):

    candidates = (
        recursively_collect_strings(
            crop_entities
        )
    )

    combined = " ".join(
        candidates
    )

    # Crop assignment primarily comes from metadata.
    # Text is only a fallback.
    metadata_search = fold_text(
        combined
    )

    text_search = fold_text(
        text
    )

    crop_ids = []

    for crop_id, aliases in (
        TARGET_CROPS.items()
    ):

        alias_matches_metadata = any(
            fold_text(alias)
            in metadata_search
            for alias in aliases
        )

        alias_matches_text = any(
            fold_text(alias)
            in text_search
            for alias in aliases
        )

        if (
            alias_matches_metadata
            or alias_matches_text
        ):

            crop_ids.append(
                crop_id
            )

    return sorted(
        set(crop_ids)
    )


# ============================================================
# HEADING DETECTION
# ============================================================

def uppercase_ratio(text):

    letters = [
        char
        for char in text
        if char.isalpha()
    ]

    if not letters:
        return 0.0

    uppercase = sum(
        1
        for char in letters
        if char.isupper()
    )

    return (
        uppercase
        /
        len(letters)
    )


def is_heading(line):

    line = line.strip()

    if not line:
        return False

    if len(line) > 160:
        return False

    if re.match(
        r"^#{1,6}\s+\S+",
        line,
    ):
        return True

    if re.match(
        r"^\d+(?:\.\d+)*[\.\)]?\s+\S+",
        line,
    ):
        return True

    if re.match(
        r"^[IVXLCDM]+[\.\)]\s+\S+",
        line,
        flags=re.IGNORECASE,
    ):
        return True

    if (
        len(line) <= 120
        and
        uppercase_ratio(line) >= 0.72
        and
        sum(
            char.isalpha()
            for char in line
        ) >= 6
    ):
        return True

    return False


# ============================================================
# SECTIONING
# ============================================================

def build_sections(text):

    text = normalize_text(
        text
    )

    if not text:
        return []

    lines = text.splitlines()

    sections = []

    current_title = ""
    current_lines = []

    def flush():

        nonlocal current_title
        nonlocal current_lines

        content = normalize_text(
            "\n".join(
                current_lines
            )
        )

        if content:

            sections.append({
                "section_title":
                    current_title,

                "text":
                    content,
            })

        current_title = ""
        current_lines = []

    for line in lines:

        clean = line.strip()

        if (
            clean
            and
            is_heading(clean)
        ):

            if current_lines:
                flush()

            current_title = clean

            current_lines.append(
                clean
            )

        else:

            current_lines.append(
                line
            )

    if current_lines:
        flush()

    if not sections:

        return [{
            "section_title":
                "",

            "text":
                text,
        }]

    return sections


# ============================================================
# ATOMIC TEXT UNITS
#
# Paragraphs are preferred.
# Large paragraphs are split on sentence boundaries.
# ============================================================

def split_sentences(text):

    text = normalize_text(
        text
    )

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def hard_split_text(
    text,
    max_chars,
):

    words = text.split()

    if not words:
        return []

    result = []
    current = []

    for word in words:

        candidate = (
            " ".join(
                current + [word]
            )
        )

        if (
            current
            and
            len(candidate)
            > max_chars
        ):

            result.append(
                " ".join(current)
            )

            current = [word]

        else:

            current.append(word)

    if current:

        result.append(
            " ".join(current)
        )

    return result


def build_atomic_units(
    section_text,
):

    section_text = normalize_text(
        section_text
    )

    paragraphs = re.split(
        r"\n\s*\n",
        section_text,
    )

    if len(paragraphs) == 1:

        # Some normalized HTML/PDF documents contain very few
        # line breaks. Sentence splitting prevents one huge atom.
        paragraphs = split_sentences(
            section_text
        )

    atoms = []

    for paragraph in paragraphs:

        paragraph = normalize_text(
            paragraph
        )

        if not paragraph:
            continue

        if len(paragraph) <= MAX_CHARS:

            atoms.append(
                paragraph
            )

            continue

        sentences = split_sentences(
            paragraph
        )

        if (
            len(sentences) > 1
        ):

            current = ""

            for sentence in sentences:

                candidate = (
                    sentence
                    if not current
                    else (
                        current
                        + " "
                        + sentence
                    )
                )

                if (
                    current
                    and
                    len(candidate)
                    > MAX_CHARS
                ):

                    atoms.append(
                        current
                    )

                    current = sentence

                else:

                    current = candidate

            if current:

                atoms.append(
                    current
                )

        else:

            atoms.extend(
                hard_split_text(
                    paragraph,
                    MAX_CHARS,
                )
            )

    return atoms


# ============================================================
# CHUNKING
# ============================================================

def trailing_overlap_atoms(
    atoms,
):

    selected = []
    total = 0

    for atom in reversed(
        atoms
    ):

        atom_len = len(atom)

        if (
            selected
            and
            total + atom_len
            > OVERLAP_CHARS
        ):

            break

        selected.append(
            atom
        )

        total += (
            atom_len
            + 1
        )

        if total >= OVERLAP_CHARS:
            break

    return list(
        reversed(selected)
    )


def chunk_section(
    section_text,
):

    atoms = build_atomic_units(
        section_text
    )

    if not atoms:
        return []

    chunks = []

    current_atoms = []

    for atom in atoms:

        candidate_atoms = (
            current_atoms
            + [atom]
        )

        candidate_text = normalize_text(
            "\n\n".join(
                candidate_atoms
            )
        )

        if (
            current_atoms
            and
            len(candidate_text)
            > TARGET_CHARS
        ):

            finished_text = normalize_text(
                "\n\n".join(
                    current_atoms
                )
            )

            if finished_text:

                chunks.append(
                    finished_text
                )

            overlap_atoms = (
                trailing_overlap_atoms(
                    current_atoms
                )
            )

            current_atoms = (
                overlap_atoms
                + [atom]
            )

            current_text = normalize_text(
                "\n\n".join(
                    current_atoms
                )
            )

            if len(current_text) > MAX_CHARS:

                current_atoms = [atom]

        else:

            current_atoms.append(
                atom
            )

    if current_atoms:

        final_text = normalize_text(
            "\n\n".join(
                current_atoms
            )
        )

        if final_text:
            chunks.append(
                final_text
            )

    # Merge very small final chunk if possible.
    if (
        len(chunks) >= 2
        and
        len(chunks[-1])
        < MIN_CHUNK_CHARS
    ):

        combined = normalize_text(
            chunks[-2]
            + "\n\n"
            + chunks[-1]
        )

        if len(combined) <= MAX_CHARS:

            chunks[-2] = combined
            chunks.pop()

    return chunks


# ============================================================
# RETRIEVAL BUCKET ASSIGNMENT
# ============================================================

def infer_retrieval_buckets(
    text,
    parent_buckets,
):

    allowed = (
        set(parent_buckets)
        &
        ALLOWED_RAG_BUCKETS
    )

    if not allowed:
        return []

    searchable = fold_text(
        text
    )

    matched = []

    for bucket in sorted(allowed):

        keywords = (
            BUCKET_KEYWORDS.get(
                bucket,
                [],
            )
        )

        if any(
            fold_text(keyword)
            in searchable
            for keyword in keywords
        ):

            matched.append(
                bucket
            )

    if matched:

        return (
            sorted(
                set(matched)
            ),
            "KEYWORD_SUBSET",
        )

    # No deterministic signal found.
    # Preserve parent-approved coverage instead of inventing
    # a bucket.
    return (
        sorted(allowed),
        "PARENT_FALLBACK",
    )


# ============================================================
# ACCEPTED DOCUMENT INPUTS
#
# accepted_manifest.jsonl is authoritative.
# Individual document registry quality_status may be stale.
# ============================================================

def load_accepted_document_units():

    rows = load_jsonl(
        ACCEPTED_MANIFEST
    )

    units = []
    rejected = []

    for row in rows:

        document_id = str(
            row.get(
                "document_id",
                "",
            )
        ).strip()

        if not document_id:

            rejected.append({
                "reason":
                    "MISSING_DOCUMENT_ID",
            })
            continue

        if (
            str(
                row.get(
                    "quality_status",
                    "",
                )
            ).upper()
            != "ACCEPTED"
        ):

            rejected.append({
                "document_id":
                    document_id,

                "reason":
                    "MANIFEST_NOT_ACCEPTED",
            })
            continue

        if (
            row.get(
                "rag_eligible"
            )
            is not True
        ):

            rejected.append({
                "document_id":
                    document_id,

                "reason":
                    "RAG_NOT_ELIGIBLE",
            })
            continue

        buckets = normalize_bucket_list(
            row.get(
                "buckets"
            )
        )

        if LEGAL_BUCKET in buckets:

            rejected.append({
                "document_id":
                    document_id,

                "reason":
                    "LEGAL_BUCKET_EXCLUDED",
            })
            continue

        normalized_path = (
            resolve_data_path(
                row.get(
                    "normalized_path"
                )
            )
        )

        if (
            normalized_path is None
            or
            not normalized_path.exists()
        ):

            rejected.append({
                "document_id":
                    document_id,

                "reason":
                    "NORMALIZED_TEXT_MISSING",

                "path":
                    str(
                        normalized_path
                    ),
            })
            continue

        text = normalize_text(
            normalized_path.read_text(
                encoding="utf-8"
            )
        )

        if not text:

            rejected.append({
                "document_id":
                    document_id,

                "reason":
                    "EMPTY_TEXT",
            })
            continue

        crop_entities = (
            row.get(
                "crop_entities",
                []
            )
        )

        units.append({
            "input_type":
                "ACCEPTED_DOCUMENT",

            "source_unit_id":
                document_id,

            "parent_document_id":
                document_id,

            "source_id":
                row.get(
                    "source_id"
                ),

            "title":
                row.get(
                    "title"
                ),

            "url":
                row.get(
                    "url"
                ),

            "published_date":
                row.get(
                    "published_date"
                ),

            "source_credibility":
                row.get(
                    "source_credibility"
                ),

            "knowledge_scope":
                row.get(
                    "knowledge_scope"
                ),

            "region":
                row.get(
                    "region"
                ),

            "local_applicability":
                row.get(
                    "local_applicability"
                ),

            "crop_entities":
                crop_entities,

            "crop_ids":
                derive_crop_ids(
                    crop_entities,
                    text,
                ),

            "parent_buckets":
                buckets,

            "quality_status":
                "ACCEPTED",

            "evidence_status":
                None,

            "chunking_strategy":
                row.get(
                    "chunking_strategy"
                ),

            "source_path":
                str(
                    normalized_path
                ),

            "text":
                text,

            "input_checksum":
                checksum_text(
                    text
                ),
        })

    return (
        units,
        rejected,
    )


# ============================================================
# VALIDATED SECTION INPUTS
# ============================================================

BAD_SECTION_STATUSES = {
    "REJECTED",
    "FAILED",
    "REVIEW_REQUIRED",
    "PENDING_REVIEW",
}


def load_validated_section_units():

    units = []
    rejected = []

    if not SECTION_REGISTRY_DIR.exists():

        return (
            units,
            rejected,
        )

    for registry_path in sorted(
        SECTION_REGISTRY_DIR.glob(
            "*.json"
        )
    ):

        row = load_json(
            registry_path
        )

        section_id = str(
            row.get(
                "section_id",
                "",
            )
        ).strip()

        if not section_id:
            continue

        if (
            row.get(
                "coverage_eligible"
            )
            is not True
        ):

            rejected.append({
                "section_id":
                    section_id,

                "reason":
                    "NOT_COVERAGE_ELIGIBLE",
            })
            continue

        evidence_status = str(
            row.get(
                "evidence_status",
                "",
            )
        ).strip().upper()

        if (
            evidence_status
            in BAD_SECTION_STATUSES
        ):

            rejected.append({
                "section_id":
                    section_id,

                "reason":
                    "BAD_EVIDENCE_STATUS",

                "evidence_status":
                    evidence_status,
            })
            continue

        buckets = normalize_bucket_list(
            row.get(
                "buckets"
            )
        )

        if LEGAL_BUCKET in buckets:

            rejected.append({
                "section_id":
                    section_id,

                "reason":
                    "LEGAL_BUCKET_EXCLUDED",
            })
            continue

        section_path = (
            resolve_data_path(
                row.get(
                    "section_path"
                )
            )
        )

        if (
            section_path is None
            or
            not section_path.exists()
        ):

            rejected.append({
                "section_id":
                    section_id,

                "reason":
                    "SECTION_TEXT_MISSING",

                "path":
                    str(
                        section_path
                    ),
            })
            continue

        text = normalize_text(
            section_path.read_text(
                encoding="utf-8"
            )
        )

        if not text:

            rejected.append({
                "section_id":
                    section_id,

                "reason":
                    "EMPTY_TEXT",
            })
            continue

        parent_document_id = str(
            row.get(
                "parent_document_id",
                "",
            )
        ).strip()

        parent = {}

        parent_path = (
            DOCUMENT_REGISTRY_DIR
            / f"{parent_document_id}.json"
        )

        if parent_path.exists():

            parent = load_json(
                parent_path
            )

        crop_entities = (
            row.get(
                "crop_entities",
                []
            )
        )

        units.append({
            "input_type":
                "VALIDATED_SECTION",

            "source_unit_id":
                section_id,

            "parent_document_id":
                parent_document_id,

            "source_id":
                row.get(
                    "source_id"
                ),

            "title":
                parent.get(
                    "title"
                ),

            "url":
                (
                    row.get(
                        "source_url"
                    )
                    or
                    parent.get(
                        "url"
                    )
                ),

            "published_date":
                parent.get(
                    "published_date"
                ),

            "source_credibility":
                parent.get(
                    "source_credibility"
                ),

            "knowledge_scope":
                row.get(
                    "knowledge_scope"
                ),

            "region":
                row.get(
                    "region"
                ),

            "local_applicability":
                row.get(
                    "local_applicability"
                ),

            "crop_entities":
                crop_entities,

            "crop_ids":
                derive_crop_ids(
                    crop_entities,
                    text,
                ),

            "parent_buckets":
                buckets,

            "quality_status":
                None,

            "evidence_status":
                (
                    evidence_status
                    or None
                ),

            "evidence_role":
                row.get(
                    "evidence_role"
                ),

            "section_mode":
                row.get(
                    "section_mode"
                ),

            "bucket_evidence":
                row.get(
                    "bucket_evidence"
                ),

            "source_path":
                str(
                    section_path
                ),

            "text":
                text,

            "input_checksum":
                checksum_text(
                    text
                ),
        })

    return (
        units,
        rejected,
    )


# ============================================================
# EXACT INPUT DEDUP
# ============================================================

def deduplicate_input_units(
    units,
):

    result = []
    duplicate_units = []

    seen = {}

    for unit in units:

        checksum = unit[
            "input_checksum"
        ]

        if checksum in seen:

            duplicate_units.append({
                "source_unit_id":
                    unit[
                        "source_unit_id"
                    ],

                "duplicate_of":
                    seen[
                        checksum
                    ],
            })

            continue

        seen[
            checksum
        ] = unit[
            "source_unit_id"
        ]

        result.append(
            unit
        )

    return (
        result,
        duplicate_units,
    )


# ============================================================
# BUILD CORPUS CHUNKS
# ============================================================

def build_chunks(
    units,
):

    chunks = []

    exact_chunk_seen = {}

    duplicate_chunks = []

    unit_stats = {}

    for unit in units:

        source_unit_id = (
            unit[
                "source_unit_id"
            ]
        )

        sections = build_sections(
            unit[
                "text"
            ]
        )

        unit_chunk_count = 0
        unit_section_count = 0

        for section_index, section in enumerate(
            sections,
            start=1,
        ):

            section_text = (
                section[
                    "text"
                ]
            )

            section_title = (
                section[
                    "section_title"
                ]
            )

            if not section_text:
                continue

            unit_section_count += 1

            section_chunks = (
                chunk_section(
                    section_text
                )
            )

            corpus_section_id = (
                f"CSEC-"
                f"{source_unit_id}-"
                f"{section_index:03d}"
            )

            for local_chunk_index, text in enumerate(
                section_chunks,
                start=1,
            ):

                text = normalize_text(
                    text
                )

                if not text:
                    continue

                text_checksum = (
                    checksum_text(
                        text
                    )
                )

                if text_checksum in exact_chunk_seen:

                    duplicate_chunks.append({
                        "source_unit_id":
                            source_unit_id,

                        "duplicate_of_chunk":
                            exact_chunk_seen[
                                text_checksum
                            ],
                    })

                    continue

                chunk_index = (
                    unit_chunk_count
                    + 1
                )

                retrieval_buckets, bucket_mode = (
                    infer_retrieval_buckets(
                        text,
                        unit[
                            "parent_buckets"
                        ],
                    )
                )

                crop_ids = (
                    derive_crop_ids(
                        unit[
                            "crop_entities"
                        ],
                        text,
                    )
                )

                if not crop_ids:

                    crop_ids = (
                        unit[
                            "crop_ids"
                        ]
                    )

                chunk_id = (
                    f"CHK-"
                    f"{source_unit_id}-"
                    f"{chunk_index:04d}-"
                    f"{text_checksum[:8]}"
                )

                record = {
                    "chunk_id":
                        chunk_id,

                    "source_unit_id":
                        source_unit_id,

                    "input_type":
                        unit[
                            "input_type"
                        ],

                    "parent_document_id":
                        unit[
                            "parent_document_id"
                        ],

                    "corpus_section_id":
                        corpus_section_id,

                    "section_index":
                        section_index,

                    "section_title":
                        section_title,

                    "chunk_index":
                        chunk_index,

                    "source_id":
                        unit[
                            "source_id"
                        ],

                    "title":
                        unit[
                            "title"
                        ],

                    "url":
                        unit[
                            "url"
                        ],

                    "published_date":
                        unit[
                            "published_date"
                        ],

                    "source_credibility":
                        unit[
                            "source_credibility"
                        ],

                    "knowledge_scope":
                        unit[
                            "knowledge_scope"
                        ],

                    "region":
                        unit[
                            "region"
                        ],

                    "local_applicability":
                        unit[
                            "local_applicability"
                        ],

                    "crop_entities":
                        unit[
                            "crop_entities"
                        ],

                    "crop_ids":
                        crop_ids,

                    "parent_buckets":
                        unit[
                            "parent_buckets"
                        ],

                    "retrieval_buckets":
                        retrieval_buckets,

                    "bucket_assignment_mode":
                        bucket_mode,

                    "quality_status":
                        unit.get(
                            "quality_status"
                        ),

                    "evidence_status":
                        unit.get(
                            "evidence_status"
                        ),

                    "evidence_role":
                        unit.get(
                            "evidence_role"
                        ),

                    "source_path":
                        unit[
                            "source_path"
                        ],

                    "char_count":
                        len(text),

                    "word_count":
                        len(
                            text.split()
                        ),

                    "text_checksum":
                        text_checksum,

                    "text":
                        text,
                }

                chunks.append(
                    record
                )

                exact_chunk_seen[
                    text_checksum
                ] = chunk_id

                unit_chunk_count += 1

        unit_stats[
            source_unit_id
        ] = {
            "input_type":
                unit[
                    "input_type"
                ],

            "input_chars":
                len(
                    unit[
                        "text"
                    ]
                ),

            "sections":
                unit_section_count,

            "chunks":
                unit_chunk_count,
        }

    return (
        chunks,
        duplicate_chunks,
        unit_stats,
    )


# ============================================================
# CORPUS AUDIT
# ============================================================

def audit_chunks(
    chunks,
    units,
):

    issues = []
    warnings = []

    chunk_ids = [
        row[
            "chunk_id"
        ]
        for row in chunks
    ]

    if (
        len(chunk_ids)
        !=
        len(set(chunk_ids))
    ):

        issues.append(
            "DUPLICATE_CHUNK_ID"
        )

    for row in chunks:

        if LEGAL_BUCKET in (
            row[
                "parent_buckets"
            ]
        ):

            issues.append({
                "code":
                    "LEGAL_BUCKET_ENTERED_RAG_CORPUS",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],
            })

        if not row[
            "text"
        ].strip():

            issues.append({
                "code":
                    "EMPTY_CHUNK",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],
            })

        if not row[
            "retrieval_buckets"
        ]:

            issues.append({
                "code":
                    "NO_RETRIEVAL_BUCKET",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],
            })

        if not row[
            "source_id"
        ]:

            issues.append({
                "code":
                    "MISSING_SOURCE_ID",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],
            })

        if (
            row[
                "char_count"
            ]
            > MAX_CHARS + OVERLAP_CHARS
        ):

            warnings.append({
                "code":
                    "LONG_CHUNK",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],

                "char_count":
                    row[
                        "char_count"
                    ],
            })

        if not row[
            "crop_ids"
        ]:

            warnings.append({
                "code":
                    "NO_TARGET_CROP_METADATA",

                "chunk_id":
                    row[
                        "chunk_id"
                    ],
            })

    input_ids = {
        unit[
            "source_unit_id"
        ]
        for unit in units
    }

    chunk_unit_ids = {
        row[
            "source_unit_id"
        ]
        for row in chunks
    }

    missing_units = sorted(
        input_ids
        -
        chunk_unit_ids
    )

    if missing_units:

        issues.append({
            "code":
                "INPUT_UNIT_WITHOUT_CHUNKS",

            "source_unit_ids":
                missing_units,
        })

    return (
        issues,
        warnings,
    )


# ============================================================
# SUMMARY
# ============================================================

def count_values(
    chunks,
    field,
):

    counter = Counter()

    for row in chunks:

        value = row.get(
            field
        )

        if isinstance(
            value,
            list,
        ):

            for item in value:
                counter[item] += 1

        elif value:

            counter[value] += 1

    return dict(
        sorted(
            counter.items()
        )
    )


def print_table_counter(
    title,
    values,
):

    print()
    print(title)

    if not values:

        print("  None")
        return

    for key, value in (
        values.items()
    ):

        print(
            f"  {key:<32} {value:>5}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 110)
    print(
        "AGRI RAG - WHOLE CORPUS BUILD"
    )
    print("=" * 110)

    print(
        "Legal policy: B06_PESTICIDE_LEGAL "
        "is EXCLUDED from text RAG corpus."
    )

    # ========================================================
    # INPUT
    # ========================================================

    (
        accepted_units,
        accepted_rejected,
    ) = load_accepted_document_units()

    (
        section_units,
        section_rejected,
    ) = load_validated_section_units()

    raw_units = (
        accepted_units
        +
        section_units
    )

    (
        units,
        duplicate_units,
    ) = deduplicate_input_units(
        raw_units
    )

    print()
    print("=" * 110)
    print("CORPUS INPUT")
    print("=" * 110)

    print(
        f"Accepted document units       : "
        f"{len(accepted_units)}"
    )

    print(
        f"Validated section units       : "
        f"{len(section_units)}"
    )

    print(
        f"Units before dedup            : "
        f"{len(raw_units)}"
    )

    print(
        f"Exact duplicate units removed : "
        f"{len(duplicate_units)}"
    )

    print(
        f"Final corpus input units      : "
        f"{len(units)}"
    )

    print(
        f"Rejected document inputs      : "
        f"{len(accepted_rejected)}"
    )

    print(
        f"Rejected section inputs       : "
        f"{len(section_rejected)}"
    )

    # Current project should contain at least the known
    # 3 accepted documents and 5 validated sections.
    if len(accepted_units) < 3:

        raise RuntimeError(
            "Expected at least 3 accepted "
            "document units."
        )

    if len(section_units) < 5:

        raise RuntimeError(
            "Expected at least 5 validated "
            "section units."
        )

    # ========================================================
    # BUILD
    # ========================================================

    (
        chunks,
        duplicate_chunks,
        unit_stats,
    ) = build_chunks(
        units
    )

    (
        issues,
        warnings,
    ) = audit_chunks(
        chunks,
        units,
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    if issues:

        status = (
            "REVIEW_REQUIRED"
        )

    else:

        status = (
            "READY_FOR_RETRIEVAL_INDEX"
        )

    total_input_chars = sum(
        len(
            unit[
                "text"
            ]
        )
        for unit in units
    )

    total_chunk_chars = sum(
        row[
            "char_count"
        ]
        for row in chunks
    )

    manifest = {
        "status":
            status,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "legal_policy": {
            "B06_PESTICIDE_LEGAL":
                "EXCLUDED_FROM_TEXT_RAG",

            "runtime_legal_source":
                (
                    "data/agri_rag/legal_bundles/"
                    "PESTICIDE_LIST_VN_CURRENT/"
                    "current_legal_records.jsonl"
                ),
        },

        "source_selection": {
            "accepted_document_units":
                len(
                    accepted_units
                ),

            "validated_section_units":
                len(
                    section_units
                ),

            "final_input_units":
                len(
                    units
                ),

            "duplicate_input_units_removed":
                len(
                    duplicate_units
                ),

            "rejected_document_inputs":
                accepted_rejected,

            "rejected_section_inputs":
                section_rejected,
        },

        "chunking": {
            "target_chars":
                TARGET_CHARS,

            "max_chars":
                MAX_CHARS,

            "overlap_chars":
                OVERLAP_CHARS,

            "minimum_chunk_chars":
                MIN_CHUNK_CHARS,

            "strategy":
                (
                    "heading-aware + paragraph/sentence "
                    "boundary chunking"
                ),
        },

        "statistics": {
            "input_char_count":
                total_input_chars,

            "chunk_char_count_including_overlap":
                total_chunk_chars,

            "chunk_count":
                len(
                    chunks
                ),

            "exact_duplicate_chunks_removed":
                len(
                    duplicate_chunks
                ),

            "by_input_type":
                count_values(
                    chunks,
                    "input_type",
                ),

            "by_source_id":
                count_values(
                    chunks,
                    "source_id",
                ),

            "by_crop_id":
                count_values(
                    chunks,
                    "crop_ids",
                ),

            "by_retrieval_bucket":
                count_values(
                    chunks,
                    "retrieval_buckets",
                ),

            "bucket_assignment_mode":
                count_values(
                    chunks,
                    "bucket_assignment_mode",
                ),
        },

        "unit_stats":
            unit_stats,

        "duplicate_units":
            duplicate_units,

        "duplicate_chunks":
            duplicate_chunks,

        "audit": {
            "issue_count":
                len(
                    issues
                ),

            "warning_count":
                len(
                    warnings
                ),

            "issues":
                issues,

            "warnings":
                warnings,
        },

        "outputs": {
            "chunks":
                str(
                    CHUNKS_FILE
                ),
        },
    }

    write_jsonl(
        CHUNKS_FILE,
        chunks,
    )

    save_json(
        CORPUS_MANIFEST_FILE,
        manifest,
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 110)
    print("SECTIONING / CHUNKING SUMMARY")
    print("=" * 110)

    print(
        f"Input characters              : "
        f"{total_input_chars}"
    )

    print(
        f"Chunks created                : "
        f"{len(chunks)}"
    )

    print(
        f"Exact duplicate chunks removed: "
        f"{len(duplicate_chunks)}"
    )

    print(
        f"Chunk chars incl. overlap     : "
        f"{total_chunk_chars}"
    )

    print_table_counter(
        "Chunks by source:",
        count_values(
            chunks,
            "source_id",
        ),
    )

    print_table_counter(
        "Chunks by crop:",
        count_values(
            chunks,
            "crop_ids",
        ),
    )

    print_table_counter(
        "Chunks by retrieval bucket:",
        count_values(
            chunks,
            "retrieval_buckets",
        ),
    )

    print_table_counter(
        "Bucket assignment mode:",
        count_values(
            chunks,
            "bucket_assignment_mode",
        ),
    )

    print()
    print("=" * 110)
    print("INPUT UNIT SUMMARY")
    print("=" * 110)

    for source_unit_id, info in (
        unit_stats.items()
    ):

        print(
            f"{source_unit_id:<24} "
            f"type={info['input_type']:<20} "
            f"chars={info['input_chars']:<7} "
            f"sections={info['sections']:<4} "
            f"chunks={info['chunks']}"
        )

    print()
    print("=" * 110)
    print("CORPUS AUDIT")
    print("=" * 110)

    print(
        f"Status        : {status}"
    )

    print(
        f"Issues        : {len(issues)}"
    )

    print(
        f"Warnings      : {len(warnings)}"
    )

    if issues:

        print()
        print("Blocking issues:")

        for issue in issues:
            print(f"  - {issue}")

    if warnings:

        print()
        print("Warnings:")

        for warning in warnings[:20]:
            print(f"  - {warning}")

        if len(warnings) > 20:

            print(
                f"  ... "
                f"{len(warnings) - 20} more"
            )

    # ========================================================
    # SAMPLE CHUNKS
    # ========================================================

    print()
    print("=" * 110)
    print("CHUNK SAMPLES")
    print("=" * 110)

    for row in chunks[:5]:

        preview = (
            row[
                "text"
            ][:260]
            .replace(
                "\n",
                " "
            )
        )

        print()
        print(
            f"{row['chunk_id']}"
        )

        print(
            f"  Source   : "
            f"{row['source_unit_id']} / "
            f"{row['source_id']}"
        )

        print(
            f"  Crop     : "
            f"{row['crop_ids']}"
        )

        print(
            f"  Buckets  : "
            f"{row['retrieval_buckets']}"
        )

        print(
            f"  Mode     : "
            f"{row['bucket_assignment_mode']}"
        )

        print(
            f"  Section  : "
            f"{row['section_title']}"
        )

        print(
            f"  Chars    : "
            f"{row['char_count']}"
        )

        print(
            f"  Preview  : "
            f"{preview}"
        )

    print()
    print("=" * 110)
    print("OUTPUT")
    print("=" * 110)

    print(
        f"Chunks manifest : "
        f"{CHUNKS_FILE}"
    )

    print(
        f"Corpus manifest : "
        f"{CORPUS_MANIFEST_FILE}"
    )

    print()

    if status == "READY_FOR_RETRIEVAL_INDEX":

        print(
            "CORPUS BUILD PASSED."
        )

        print(
            "NEXT: build BM25 and dense retrieval indexes."
        )

    else:

        print(
            "CORPUS BUILD REQUIRES REVIEW."
        )

        print(
            "Do not build retrieval indexes yet."
        )


if __name__ == "__main__":
    main()
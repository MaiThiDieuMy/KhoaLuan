import json

from src.agri_rag.schemas.document import DocumentRecord


doc = DocumentRecord(
    document_id="DOC0001",
    source_id="S02_EXTENSION",
    url="https://example.com/document",

    title="Kỹ thuật chăm sóc rau",
    published_date="2026-01-01",

    document_family="technical_guide",

    buckets=[
        "B02_WATER",
        "B05_WEATHER_CARE",
    ],

    crop_entities=[
        "cai_xanh",
    ],

    knowledge_scope="crop_specific",
    region="VIETNAM",

    source_credibility="HIGH",
    local_applicability="VIETNAM_GENERAL",
)

print(
    json.dumps(
        doc.to_dict(),
        ensure_ascii=False,
        indent=2,
    )
)
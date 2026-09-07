from pathlib import Path
from urllib.parse import urlparse
import hashlib
import requests


RAW_DIR = Path("data/agri_rag/raw")

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36 "
        "AgriRAGResearch/1.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "application/pdf;q=0.8,*/*;q=0.7"
    ),
}


def _detect_extension(
    url: str,
    content_type: str,
) -> str:
    """
    Xác định file tải về là HTML, PDF hay định dạng khác.
    """

    clean_content_type = (
        content_type
        .split(";")[0]
        .strip()
        .lower()
    )

    if clean_content_type == "application/pdf":
        return ".pdf"

    if clean_content_type in {
        "text/html",
        "application/xhtml+xml",
    }:
        return ".html"

    if (
        "wordprocessingml" in clean_content_type
        or "msword" in clean_content_type
    ):
        return ".docx"

    # Fallback theo URL nếu server trả content-type không rõ
    path = urlparse(url).path.lower()

    if path.endswith(".pdf"):
        return ".pdf"

    if path.endswith(".docx"):
        return ".docx"

    return ".html"


def download_url(
    url: str,
    document_id: str,
) -> dict:
    """
    Download một URL và lưu bản raw.

    Không:
    - extract nội dung
    - normalize
    - sửa nội dung
    - bỏ SSL verification

    Returns:
        dict chứa metadata của lần download.
    """

    print(f"[DOWNLOAD] {document_id}")
    print(f"[URL] {url}")

    try:
        response = requests.get(
            url,
            timeout=45,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        return {
            "success": False,
            "document_id": document_id,
            "url": url,
            "error": str(exc),
        }

    content = response.content

    if not content:
        return {
            "success": False,
            "document_id": document_id,
            "url": url,
            "error": "EMPTY_RESPONSE",
        }

    content_type = response.headers.get(
        "Content-Type",
        "",
    )

    extension = _detect_extension(
        response.url,
        content_type,
    )

    output_path = (
        RAW_DIR
        / f"{document_id}{extension}"
    )

    output_path.write_bytes(content)

    checksum = hashlib.sha256(
        content
    ).hexdigest()

    return {
        "success": True,
        "document_id": document_id,
        "requested_url": url,
        "final_url": response.url,
        "http_status": response.status_code,
        "content_type": content_type,
        "file_size_bytes": len(content),
        "checksum": checksum,
        "raw_path": str(output_path),
    }
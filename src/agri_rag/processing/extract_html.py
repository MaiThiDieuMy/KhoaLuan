import re
from pathlib import Path

from bs4 import BeautifulSoup


REMOVE_TAGS = [
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "nav",
    "footer",
    "aside",
]


# Các selector phổ biến mà website tin tức / cơ quan nhà nước
# thường dùng để chứa nội dung bài.
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",

    ".article-content",
    ".article-detail",

    ".detail-content",
    ".detail-news",

    ".news-content",
    ".news-detail",

    ".post-content",
    ".entry-content",

    ".content-detail",
    ".content-news",
    ".content-body",

    "#content",
]


MIN_CONTENT_CHARS = 200


def _normalize_whitespace(text: str) -> str:
    """
    Chỉ chuẩn hóa whitespace cơ bản trong extraction.
    Chưa phải bước normalization của RAG.
    """

    lines = []

    for raw_line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            raw_line,
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def _get_text(element) -> str:

    if element is None:
        return ""

    text = element.get_text(
        "\n",
        strip=True,
    )

    return _normalize_whitespace(
        text
    )


def _extract_title(soup):
    """
    Ưu tiên:
    1. og:title
    2. H1
    3. HTML title
    """

    og_title = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        },
    )

    if (
        og_title
        and og_title.get("content")
    ):
        return og_title[
            "content"
        ].strip()

    h1 = soup.find("h1")

    if h1:
        title = _get_text(h1)

        if title:
            return title

    if soup.title:
        return _get_text(
            soup.title
        )

    return None


def extract_html(path: str) -> dict:
    """
    Extract text từ raw HTML.

    Không:
    - tóm tắt
    - rewrite
    - chunk
    - dùng LLM

    Nếu không lấy được nội dung đủ dài,
    trả REVIEW_REQUIRED thay vì giả SUCCESS.
    """

    html_path = Path(path)

    html = html_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    # ======================================================
    # 1. Lấy title trước khi remove các tag
    # ======================================================

    title = _extract_title(
        soup
    )

    # ======================================================
    # 2. Bỏ các vùng chắc chắn không cần
    # ======================================================

    for tag_name in REMOVE_TAGS:

        for tag in soup.find_all(
            tag_name
        ):
            tag.decompose()

    # ======================================================
    # 3. Tìm candidate content
    # ======================================================

    candidates = []

    for selector in CONTENT_SELECTORS:

        elements = soup.select(
            selector
        )

        for element in elements:

            text = _get_text(
                element
            )

            if text:

                candidates.append({
                    "selector": selector,
                    "text": text,
                    "char_count": len(text),
                })

    # ======================================================
    # 4. Chọn candidate dài nhất
    # ======================================================

    if candidates:

        best_candidate = max(
            candidates,
            key=lambda item:
                item["char_count"],
        )

        text = best_candidate[
            "text"
        ]

        selected_selector = (
            best_candidate[
                "selector"
            ]
        )

    else:

        text = ""
        selected_selector = None

    # ======================================================
    # 5. Nếu candidate quá ngắn → fallback BODY
    # ======================================================

    if (
        len(text)
        < MIN_CONTENT_CHARS
    ):

        body_text = _get_text(
            soup.body
            if soup.body
            else soup
        )

        if len(body_text) > len(text):

            text = body_text

            selected_selector = (
                "body_fallback"
            )

    # ======================================================
    # 6. Xác định trạng thái
    # ======================================================

    char_count = len(text)

    if (
        char_count
        < MIN_CONTENT_CHARS
    ):
        status = "REVIEW_REQUIRED"

    else:
        status = "SUCCESS"

    return {
        "title": title,

        "text": text,

        "char_count": (
            char_count
        ),

        "selected_selector": (
            selected_selector
        ),

        "extraction_method": (
            "BEAUTIFULSOUP_HTML"
        ),

        "status": status,
    }
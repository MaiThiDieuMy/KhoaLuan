from pathlib import Path

import pymupdf


def extract_pdf(path: str) -> dict:
    """
    Extract text trực tiếp từ PDF bằng PyMuPDF.

    Nếu PDF gần như không có text layer,
    đánh dấu OCR_REQUIRED.

    Không tự OCR ở bước này.
    """

    pdf_path = Path(path)

    document = pymupdf.open(
        pdf_path
    )

    pages = []

    total_char_count = 0

    for index, page in enumerate(
        document,
        start=1,
    ):
        text = page.get_text(
            "text"
        ).strip()

        char_count = len(text)

        total_char_count += (
            char_count
        )

        pages.append({
            "page_number": index,
            "text": text,
            "char_count": char_count,
        })

    page_count = len(pages)

    document.close()

    full_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    # ------------------------------------------------------
    # Heuristic để phát hiện PDF scan / không có text layer
    # ------------------------------------------------------

    average_chars_per_page = (
        total_char_count / page_count
        if page_count > 0
        else 0
    )

    if (
        total_char_count < 500
        or average_chars_per_page < 50
    ):
        status = "OCR_REQUIRED"
    else:
        status = "SUCCESS"

    return {
        "page_count": page_count,
        "pages": pages,
        "text": full_text,
        "char_count": total_char_count,
        "average_chars_per_page": (
            average_chars_per_page
        ),
        "extraction_method": "PYMUPDF_TEXT",
        "status": status,
    }
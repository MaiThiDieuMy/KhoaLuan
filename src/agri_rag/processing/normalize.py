import hashlib
import re
import unicodedata


NORMALIZATION_METHOD = "SAFE_TEXT_NORMALIZATION_V1"


def normalize_text(text: str) -> str:
    """
    Chuẩn hóa text ở mức an toàn.

    Có làm:
    - Unicode NFC
    - line ending
    - non-breaking space
    - zero-width character
    - khoảng trắng thừa
    - dòng trắng thừa

    Không làm:
    - sửa chính tả
    - rewrite nội dung
    - dùng LLM
    - tự đoán từ bị dính
    """

    if not text:
        return ""

    # 1. Unicode
    text = unicodedata.normalize(
        "NFC",
        text,
    )

    # 2. Line ending
    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    # 3. Invisible / special spaces
    text = text.replace(
        "\u00a0",
        " ",
    )

    text = text.replace(
        "\u200b",
        "",
    )

    text = text.replace(
        "\ufeff",
        "",
    )

    # 4. Normalize whitespace theo từng dòng
    cleaned_lines = []

    for raw_line in text.split("\n"):

        line = re.sub(
            r"[ \t]+",
            " ",
            raw_line,
        ).strip()

        cleaned_lines.append(
            line
        )

    text = "\n".join(
        cleaned_lines
    )

    # 5. Không để quá 2 newline liên tục
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def text_sha256(text: str) -> str:
    """
    Tạo checksum cho normalized text.
    """

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()
import re


def validate_filename(file_name: str, max_length: int = 255) -> tuple[bool, str]:
    if not file_name:
        return False, "ファイル名が空です"

    if not re.match(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$", file_name):
        return False, "ファイル名には英小文字、数字、ハイフンのみ使用できます"

    if len(file_name) > max_length:
        return False, f"ファイル名が長すぎます。{max_length}文字以内にしてください"

    return True, ""

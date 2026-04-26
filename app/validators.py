import re

from pydantic import BaseModel, ValidationError, field_validator


class PhoneInput(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def normalize_and_validate_phone(cls, value: str) -> str:
        def is_ru_kz(phone_digits: str) -> bool:
            return phone_digits.startswith("7")

        def is_belarus(phone_digits: str) -> bool:
            return phone_digits.startswith("375")

        # 1) Clean input from spaces, dashes and brackets.
        raw = (value or "").strip()
        if not raw:
            raise ValueError("empty")
        cleaned = re.sub(r"[^\d+]", "", raw)

        # 2) Common RU local format: 8XXXXXXXXXX -> 7XXXXXXXXXX.
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = f"7{cleaned[1:]}"

        # 3) Work in pure digits regardless of leading plus sign.
        digits = cleaned[1:] if cleaned.startswith("+") else cleaned
        if not digits.isdigit():
            raise ValueError("not_digits")

        # RU/KZ local mobile format like 9XXXXXXXXX -> normalize to 7XXXXXXXXXX.
        if len(digits) == 10 and digits.startswith("9"):
            digits = f"7{digits}"

        # 4) Allow only Russia/Kazakhstan (+7...) and Belarus (+375...).
        if is_ru_kz(digits):
            if len(digits) != 11:
                raise ValueError("bad_length_ru_kz")
            return digits

        if is_belarus(digits):
            if len(digits) != 12:
                raise ValueError("bad_length_by")
            return digits

        raise ValueError("unsupported_country")


def normalize_phone(raw: str) -> str | None:
    try:
        return PhoneInput(phone=raw).phone
    except ValidationError:
        return None


def normalize_manager_group_id(raw_group_id: str) -> int:
    text = (raw_group_id or "").strip()
    if not text:
        raise RuntimeError("MANAGERS_GROUP_ID is required")
    if not re.fullmatch(r"-?\d+", text):
        raise RuntimeError("MANAGERS_GROUP_ID must be numeric")

    if text.startswith("-100"):
        return int(text)

    digits = text.lstrip("-")
    if len(digits) <= 11:
        return int(f"-100{digits}")
    return -int(digits)

import re
from datetime import datetime, timezone

DISPOSABLE_DOMAINS = {"mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com"}


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+38{digits}"
    if digits.startswith("80") and len(digits) == 11:
        return f"+3{digits}"
    return f"+{digits}" if digits else phone


def is_disposable_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in DISPOSABLE_DOMAINS


def quarantine_score(
    *,
    honeypot: str | None,
    form_started_at: datetime | None,
    email: str | None,
    phone: str,
) -> int:
    score = 0
    if honeypot:
        score += 80
    if form_started_at is not None:
        started = form_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - started).total_seconds()
        if delta < 2:
            score += 40
    if is_disposable_email(email):
        score += 50
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        score += 30
    if digits and digits == digits[0] * len(digits):
        score += 40
    return min(score, 100)

SUBJECT_MAX = {
    "ukr": 200,
    "math": 200,
    "history": 200,
    "eng": 200,
    "bio": 200,
    "geo": 200,
}


def score_diagnostic(subject: str, answers: dict) -> tuple[int, int, str, str]:
    """Stub scorer: correct keys ending with _ok or truthy values count."""
    total = max(len(answers), 1)
    correct = 0
    for key, value in answers.items():
        if value is True or value == 1 or str(key).endswith("_ok"):
            correct += 1
        elif isinstance(value, str) and value.lower() in {"a", "correct", "true"}:
            correct += 1
    raw = int(round((correct / total) * SUBJECT_MAX.get(subject, 200)))
    percentile = min(99, max(1, int(raw / 2)))
    if raw >= 160:
        track, segment = "advanced", "premium_fast_track"
    elif raw >= 120:
        track, segment = "standard", "standard_cohort"
    elif raw >= 80:
        track, segment = "foundation", "demo_then_standard"
    else:
        track, segment = "intensive", "diagnostic_consult"
    return raw, percentile, track, segment

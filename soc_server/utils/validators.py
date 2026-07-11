def require_non_empty(value: str, field_name: str) -> str:
    """Validate required text fields for future API payloads."""

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned

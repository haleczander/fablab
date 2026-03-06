def normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().lower().replace("-", "").replace(":", "").replace(".", "")
    if len(raw) != 12 or any(ch not in "0123456789abcdef" for ch in raw):
        return None
    if raw == "000000000000":
        return None
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))

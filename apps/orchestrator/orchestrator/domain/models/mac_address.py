from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MacAddress:
    value: str

    @classmethod
    def parse(cls, value: str | None) -> "MacAddress | None":
        if value is None:
            return None
        raw = value.strip().lower().replace("-", "").replace(":", "").replace(".", "")
        if len(raw) != 12 or any(ch not in "0123456789abcdef" for ch in raw):
            return None
        if raw == "000000000000":
            return None
        return cls(":".join(raw[i : i + 2] for i in range(0, 12, 2)))

    def __str__(self) -> str:
        return self.value

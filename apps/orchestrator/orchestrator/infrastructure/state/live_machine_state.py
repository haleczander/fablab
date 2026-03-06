from threading import Lock

_state: dict[str, dict[str, str | float | None]] = {}
_lock = Lock()


def upsert_machine_state(printer_id: str, payload: dict[str, str | float | None]) -> None:
    if not printer_id:
        return
    with _lock:
        _state[printer_id] = payload


def get_machine_state(printer_id: str) -> dict[str, str | float | None] | None:
    if not printer_id:
        return None
    with _lock:
        row = _state.get(printer_id)
        return dict(row) if row else None


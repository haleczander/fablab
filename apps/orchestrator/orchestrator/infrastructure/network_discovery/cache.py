from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

_snapshot_lock = Lock()
_snapshot_rows: dict[str, dict[str, str | bool | int | float | None]] = {}


def replace_snapshot(rows: list[dict[str, str | bool | int | float | None]]) -> None:
    keyed: dict[str, dict[str, str | bool | int | float | None]] = {}
    for row in rows:
        key = str(
            row.get("device_mac")
            or row.get("device_serial")
            or row.get("device_ip")
            or ""
        ).strip()
        if not key:
            continue
        keyed[key] = row
    with _snapshot_lock:
        _snapshot_rows.clear()
        _snapshot_rows.update(keyed)


def build_rows_from_discovery(
    discovered: dict[str, tuple[str | None, str | None, str | None, bool]],
    arp: dict[str, str],
) -> list[dict[str, str | bool | int | float | None]]:
    stamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, str | bool | int | float | None]] = []
    for ip, host in discovered.items():
        adapter_name, model_hint, serial_hint, reachable = host
        status = "ON" if reachable else "OFF"
        rows.append(
            {
                "device_ip": ip,
                "device_mac": arp.get(ip),
                "device_serial": serial_hint,
                "device_id": None,
                "detected_adapter": adapter_name,
                "detected_model": model_hint,
                "status": status,
                "current_job_id": None,
                "progress_pct": None,
                "nozzle_temp_c": None,
                "bed_temp_c": None,
                "last_heartbeat_at": stamp,
                "is_bound": False,
                "is_ignored": False,
                "printer_id": None,
                "printer_model": None,
            }
        )
    rows.sort(key=lambda item: str(item.get("device_ip") or ""))
    return rows


def list_snapshot_rows() -> list[dict[str, str | bool | int | float | None]]:
    with _snapshot_lock:
        rows = list(_snapshot_rows.values())
    rows.sort(key=lambda item: str(item.get("device_ip") or ""))
    return rows

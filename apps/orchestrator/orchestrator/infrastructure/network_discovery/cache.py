from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from orchestrator.domain.models import Network

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


def build_rows_from_discovery(network: Network) -> list[dict[str, str | bool | int | float | None]]:
    stamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, str | bool | int | float | None]] = []
    for device in network.devices:
        ip = str(device.ip) if device.ip else None
        mac = str(device.mac) if device.mac else None
        status = device.params.status or "OFF"
        rows.append(
            {
                "device_ip": ip,
                "device_mac": mac,
                "device_serial": device.serial,
                "device_id": None,
                "detected_adapter": str(device.type),
                "detected_model": device.model,
                "status": status,
                "current_job_id": device.params.current_job_id,
                "progress_pct": device.params.progress_pct,
                "nozzle_temp_c": device.params.nozzle_temp_c,
                "bed_temp_c": device.params.bed_temp_c,
                "last_heartbeat_at": device.params.last_heartbeat_at or stamp,
                "is_bound": False,
                "is_ignored": device.ignored,
                "printer_id": device.business_id,
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

import asyncio
import ipaddress
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlmodel import Session, select

from orchestrator.application.dependencies import get
from orchestrator.application.use_cases.list_bindings import ListBindingsUseCase
from orchestrator.application.use_cases.list_external_devices import ListExternalDevicesUseCase
from orchestrator.domain.models import Device, DeviceParams, DeviceType, IpAddress, MacAddress, Network, NetworkRange
from orchestrator.domain.models import PrinterBinding
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.cache import build_rows_from_discovery, list_snapshot_rows, replace_snapshot
from orchestrator.infrastructure.network_discovery.device_probers import probe_device
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter
from orchestrator.infrastructure.persistence.db import engine
from orchestrator.infrastructure.state.live_machine_state import upsert_machine_state


def _read_arp_table() -> dict[str, str]:
    table: dict[str, str] = {}
    try:
        with open("/proc/net/arp", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return table
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        ip = parts[0]
        parsed = MacAddress.parse(parts[3])
        if parsed:
            table[ip] = str(parsed)
    return table


def _http_json(ip: str, path: str, timeout_s: float) -> tuple[int, dict | None]:
    request = Request(url=f"http://{ip}{path}", method="GET")
    try:
        with urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="ignore")
            if not body:
                return response.status, None
            return response.status, json.loads(body)
    except HTTPError as err:
        return err.code, None
    except (URLError, TimeoutError, json.JSONDecodeError):
        return 0, None

def _map_prusalink_state(raw_state: str) -> str:
    normalized = raw_state.upper()
    mapping = {
        "IDLE": "IDLE",
        "READY": "IDLE",
        "FINISHED": "IDLE",
        "STOPPED": "IDLE",
        "PRINTING": "PRINTING",
        "PAUSED": "IN_USE",
        "BUSY": "IN_USE",
        "ATTENTION": "ERROR",
        "ERROR": "ERROR",
    }
    return mapping.get(normalized, "ON")


def _refresh_bound_printers(session: Session, timeout_s: float, now: datetime) -> int:
    updated = 0
    bindings = [row for row in session.exec(select(PrinterBinding)).all() if row.printer_id]
    snapshot = list_snapshot_rows()

    by_mac: dict[str, dict[str, str | bool | int | float | None]] = {}
    for row in snapshot:
        mac = str(row.get("device_mac") or "").strip()
        if mac:
            by_mac[mac] = row

    for binding in bindings:
        observed = by_mac.get(binding.printer_mac)
        if observed and observed.get("device_ip"):
            observed_ip = str(observed.get("device_ip"))
            if binding.printer_ip != observed_ip:
                binding.printer_ip = observed_ip
                session.add(binding)

        adapter_name = str(observed.get("detected_adapter") or "").lower() if observed else ""
        if adapter_name != "prusalink":
            continue
        if not binding.printer_ip:
            continue

        ip = binding.printer_ip
        status_code, status_payload = _http_json(ip, "/api/v1/status", timeout_s)
        if status_code != 200 or not isinstance(status_payload, dict):
            continue

        info_code, info_payload = _http_json(ip, "/api/v1/info", timeout_s)
        printer = status_payload.get("printer") or {}
        job = status_payload.get("job") or {}
        raw_state = str(printer.get("state", "ON"))

        status = _map_prusalink_state(raw_state)
        progress = job.get("progress")
        nozzle = printer.get("temp_nozzle")
        bed = printer.get("temp_bed")
        current_job_id = str(job.get("id")) if job.get("id") is not None else None
        upsert_machine_state(
            binding.printer_id,
            {
                "printer_id": binding.printer_id,
                "status": status,
                "current_job_id": current_job_id,
                "progress_pct": progress,
                "nozzle_temp_c": nozzle,
                "bed_temp_c": bed,
                "last_heartbeat_at": now.isoformat(),
            },
        )
        if info_code == 200 and isinstance(info_payload, dict) and info_payload.get("ip"):
            binding.printer_ip = str(info_payload.get("ip"))
            session.add(binding)
        updated += 1
    return updated


def run_discovery_once(
    cidr: str,
    timeout_s: float,
    refresh_bound: bool = False,
) -> int:
    arp: dict[str, str] = {}
    scanner = ScapyArpNeighborScanner()
    network = ipaddress.ip_network(cidr, strict=False)
    arp.update(scanner.scan(network=str(network.network_address), subnet_mask=str(network.netmask), timeout_s=timeout_s))
    arp.update(_read_arp_table())

    network_range = ipaddress.ip_network(cidr, strict=False)
    candidate_ips: list[str] = []
    for ip in sorted(arp):
        try:
            if ipaddress.ip_address(ip) in network_range:
                candidate_ips.append(ip)
        except ValueError:
            continue

    discovered = Network(range=NetworkRange.parse(cidr))
    with ThreadPoolExecutor(max_workers=min(24, len(candidate_ips) or 1)) as pool:
        futures = {pool.submit(probe_device, ip, timeout_s): ip for ip in candidate_ips}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                probe = future.result()
            except Exception:
                probe = None
            device = Device(
                mac=MacAddress.parse(arp.get(ip)),
                ip=IpAddress.parse(ip),
                type=DeviceType.ARP_NEIGHBOR,
                params=DeviceParams(status="ON"),
            )
            if probe and probe.reachable:
                device.type = DeviceType.from_detected_adapter(probe.adapter_name)
                device.serial = probe.serial_hint
                device.model = probe.model_hint
            discovered.merge_device(device)

    replace_snapshot(build_rows_from_discovery(discovered))
    updated = len(discovered.devices)
    if refresh_bound:
        updated += refresh_bound_printers_once(timeout_s)
    return updated


def refresh_bound_printers_once(timeout_s: float) -> int:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        updated = _refresh_bound_printers(session, timeout_s, now)
        session.commit()
    return updated


async def _notify_current_rows() -> None:
    rows = get(ListBindingsUseCase).execute(include_ignored=True)
    external_rows = get(ListExternalDevicesUseCase).execute()
    notifications = get(WebSocketNotificationAdapter)
    await notifications.notify_device_rows(rows)
    await notifications.notify_external_rows(external_rows)


async def discovery_loop(
    stop_event: asyncio.Event,
    cidr: str,
    timeout_s: float,
    interval_s: float,
) -> None:
    try:
        network_range = NetworkRange.parse(cidr)
    except ValueError:
        return

    while not stop_event.is_set():
        try:
            updated = await asyncio.to_thread(
                run_discovery_once,
                cidr=network_range.cidr,
                timeout_s=timeout_s,
                refresh_bound=False,
            )
            if updated > 0:
                await _notify_current_rows()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
        except TimeoutError:
            continue


async def bound_refresh_loop(
    stop_event: asyncio.Event,
    timeout_s: float,
    interval_s: float,
) -> None:
    while not stop_event.is_set():
        try:
            updated = await asyncio.to_thread(refresh_bound_printers_once, timeout_s=timeout_s)
            if updated > 0:
                await _notify_current_rows()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
        except TimeoutError:
            continue

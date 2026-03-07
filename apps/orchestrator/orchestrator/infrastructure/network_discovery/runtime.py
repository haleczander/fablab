import asyncio
import ipaddress
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlmodel import Session, select

from orchestrator.api.events import broadcast_machines
from orchestrator.application.app_services import FleetViewService
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import PrinterBinding
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.cache import build_rows_from_discovery, list_snapshot_rows, replace_snapshot
from orchestrator.infrastructure.network_discovery.device_probers import probe_device
from orchestrator.infrastructure.persistence.db import engine
from orchestrator.infrastructure.persistence.repositories import SqlModelPrinterBindingRepository
from orchestrator.infrastructure.state.live_machine_state import upsert_machine_state


def _parse_cidrs(raw: str) -> list[str]:
    cidrs: list[str] = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        ipaddress.ip_network(item, strict=False)
        cidrs.append(item)
    return cidrs


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
        mac = normalize_mac(parts[3])
        if mac:
            table[ip] = mac
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


def persist_discovery(
    discovered: dict[str, tuple[str | None, str | None, str | None, bool]],
    arp: dict[str, str],
    timeout_s: float,
    refresh_bound: bool = False,
) -> int:
    now = datetime.now(timezone.utc)
    updated = 0

    with Session(engine) as session:
        for ip, host in discovered.items():
            adapter_name, model_hint, serial_hint, reachable = host
            mac = arp.get(ip)
            if not mac:
                continue
            binding = session.exec(select(PrinterBinding).where(PrinterBinding.printer_mac == mac)).first()
            if binding:
                binding.printer_ip = ip
                session.add(binding)
                updated += 1

        if refresh_bound:
            updated += _refresh_bound_printers(session, timeout_s, now)

        session.commit()

    return updated


def run_discovery_once(
    cidrs: list[str],
    timeout_s: float,
    max_hosts: int,
    refresh_bound: bool = False,
) -> int:
    arp: dict[str, str] = {}
    scanner = ScapyArpNeighborScanner()
    for cidr in cidrs:
        network = ipaddress.ip_network(cidr, strict=False)
        arp.update(scanner.scan(network=str(network.network_address), subnet_mask=str(network.netmask), timeout_s=timeout_s))
    arp.update(_read_arp_table())

    candidate_ips: list[str] = []
    for ip in sorted(arp.keys()):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if any(addr in ipaddress.ip_network(cidr, strict=False) for cidr in cidrs):
            candidate_ips.append(ip)
    if max_hosts > 0:
        candidate_ips = candidate_ips[:max_hosts]

    discovered: dict[str, tuple[str | None, str | None, str | None, bool]] = {}
    with ThreadPoolExecutor(max_workers=min(24, len(candidate_ips) or 1)) as pool:
        futures = {pool.submit(probe_device, ip, timeout_s): ip for ip in candidate_ips}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                probe = future.result()
            except Exception:
                probe = None
            if probe and probe.reachable:
                discovered[ip] = (probe.adapter_name, probe.model_hint, probe.serial_hint, True)
            else:
                discovered[ip] = ("arp-neighbor", None, None, True)

    replace_snapshot(build_rows_from_discovery(discovered=discovered, arp=arp))
    updated = len(discovered)
    if refresh_bound:
        updated += refresh_bound_printers_once(timeout_s)
    return updated


def refresh_bound_printers_once(timeout_s: float) -> int:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        updated = _refresh_bound_printers(session, timeout_s, now)
        session.commit()
    return updated


async def discovery_loop(
    stop_event: asyncio.Event,
    cidrs_raw: str,
    timeout_s: float,
    max_hosts: int,
    interval_s: float,
) -> None:
    try:
        cidrs = _parse_cidrs(cidrs_raw)
    except ValueError:
        return
    if not cidrs:
        return

    while not stop_event.is_set():
        try:
            updated = await asyncio.to_thread(
                run_discovery_once,
                cidrs=cidrs,
                timeout_s=timeout_s,
                max_hosts=max_hosts,
                refresh_bound=False,
            )
            if updated > 0:
                with Session(engine) as session:
                    fleet = FleetViewService(
                        binding_repo=SqlModelPrinterBindingRepository(session),
                        discovery_snapshot_provider=list_snapshot_rows,
                    )
                    await broadcast_machines("machines_updated", fleet.machine_states_payload())
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
                with Session(engine) as session:
                    fleet = FleetViewService(
                        binding_repo=SqlModelPrinterBindingRepository(session),
                        discovery_snapshot_provider=list_snapshot_rows,
                    )
                    await broadcast_machines("machines_updated", fleet.machine_states_payload())
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
        except TimeoutError:
            continue

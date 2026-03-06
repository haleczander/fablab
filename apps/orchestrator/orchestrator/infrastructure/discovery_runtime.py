import asyncio
import ipaddress
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlmodel import Session, select

from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import DeviceRuntime, PrinterBinding, PrinterRuntime
from orchestrator.infrastructure.db import engine
from orchestrator.infrastructure.discovery import scan_cidr


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


def _scan_arp_with_scapy(cidrs: list[str], timeout_s: float) -> dict[str, str]:
    try:
        from scapy.all import ARP, Ether, srp  # type: ignore
    except Exception:
        return {}

    table: dict[str, str] = {}
    for cidr in cidrs:
        try:
            packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr)
            answered, _ = srp(packet, timeout=max(0.3, min(timeout_s, 2.5)), verbose=False)
        except Exception:
            continue
        for _, response in answered:
            ip = getattr(response, "psrc", None)
            mac = normalize_mac(getattr(response, "hwsrc", None))
            if ip and mac:
                table[str(ip)] = mac
    return table


def _ip_in_any_cidr(ip: str, cidrs: list[str]) -> bool:
    addr = ipaddress.ip_address(ip)
    return any(addr in ipaddress.ip_network(cidr, strict=False) for cidr in cidrs)


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


def run_discovery_once(cidrs: list[str], timeout_s: float, max_hosts: int) -> int:
    discovered: dict[str, tuple[str | None, str | None, str | None, bool]] = {}
    for cidr in cidrs:
        for ip, probe in scan_cidr(cidr, timeout_s=timeout_s, max_hosts=max_hosts):
            discovered[ip] = (probe.adapter_name, probe.model_hint, probe.serial_hint, True)

    arp = _scan_arp_with_scapy(cidrs=cidrs, timeout_s=timeout_s)
    arp.update(_read_arp_table())
    for ip, mac in arp.items():
        if not mac:
            continue
        if not _ip_in_any_cidr(ip, cidrs):
            continue
        if ip not in discovered:
            discovered[ip] = ("arp-neighbor", None, None, True)

    now = datetime.now(timezone.utc)
    updated = 0

    with Session(engine) as session:
        for ip, (adapter_name, model_hint, serial_hint, reachable) in discovered.items():
            mac = arp.get(ip)

            device = None
            if serial_hint:
                device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_serial == serial_hint)).first()
            if not device and mac:
                device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_mac == mac)).first()
            if not device:
                device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == ip)).first()
            if not device:
                device = DeviceRuntime(device_ip=ip)

            device.device_ip = ip
            if mac:
                device.device_mac = mac
            if serial_hint:
                device.device_serial = serial_hint
            device.probe_reachable = reachable
            if adapter_name:
                device.detected_adapter = adapter_name
            if model_hint:
                device.detected_model = model_hint
            if device.status == "OFF":
                device.status = "ON"
            device.last_heartbeat_at = now

            if adapter_name == "prusalink":
                info_status, info_payload = _http_json(ip, "/api/v1/info", timeout_s)
                if info_status == 200 and isinstance(info_payload, dict):
                    serial = info_payload.get("serial")
                    if serial:
                        device.device_serial = str(serial).strip()
                    if not device.detected_model:
                        maybe_model = str(info_payload.get("model") or "").strip()
                        if maybe_model:
                            device.detected_model = maybe_model

                status_code, status_payload = _http_json(ip, "/api/v1/status", timeout_s)
                if status_code == 200 and isinstance(status_payload, dict):
                    printer = status_payload.get("printer") or {}
                    job = status_payload.get("job") or {}
                    raw_state = str(printer.get("state", "ON"))
                    device.status = _map_prusalink_state(raw_state)
                    device.progress_pct = job.get("progress")
                    device.nozzle_temp_c = printer.get("temp_nozzle")
                    device.bed_temp_c = printer.get("temp_bed")
                    device.current_job_id = str(job.get("id")) if job.get("id") is not None else None

            binding = None
            effective_serial = device.device_serial or serial_hint
            if effective_serial:
                binding = session.exec(select(PrinterBinding).where(PrinterBinding.printer_serial == effective_serial)).first()
            if not binding and mac:
                binding = session.exec(select(PrinterBinding).where(PrinterBinding.printer_mac == mac)).first()
            if binding:
                # Keep printer routing usable when DHCP changes IP.
                binding.printer_ip = ip
                if effective_serial and not binding.printer_serial:
                    binding.printer_serial = effective_serial
                device.is_bound = True
                device.bound_printer_id = binding.printer_id

                runtime = session.exec(
                    select(PrinterRuntime).where(PrinterRuntime.printer_id == binding.printer_id)
                ).first()
                if not runtime:
                    runtime = PrinterRuntime(printer_id=binding.printer_id)
                runtime.status = device.status
                runtime.progress_pct = device.progress_pct
                runtime.nozzle_temp_c = device.nozzle_temp_c
                runtime.bed_temp_c = device.bed_temp_c
                runtime.current_job_id = device.current_job_id
                runtime.last_printer_ip = ip
                runtime.last_printer_mac = mac
                runtime.last_printer_serial = effective_serial
                runtime.last_heartbeat_at = now
                session.add(runtime)

            session.add(device)
            if binding:
                session.add(binding)
            updated += 1

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
            await asyncio.to_thread(
                run_discovery_once,
                cidrs=cidrs,
                timeout_s=timeout_s,
                max_hosts=max_hosts,
            )
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
        except TimeoutError:
            continue

import asyncio
import ipaddress
from datetime import datetime, timezone

from sqlmodel import Session, select

from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import DeviceRuntime, PrinterBinding
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


def _ip_in_any_cidr(ip: str, cidrs: list[str]) -> bool:
    addr = ipaddress.ip_address(ip)
    return any(addr in ipaddress.ip_network(cidr, strict=False) for cidr in cidrs)


def run_discovery_once(cidrs: list[str], timeout_s: float, max_hosts: int) -> int:
    discovered: dict[str, tuple[str | None, str | None, bool]] = {}
    for cidr in cidrs:
        for ip, probe in scan_cidr(cidr, timeout_s=timeout_s, max_hosts=max_hosts):
            discovered[ip] = (probe.adapter_name, probe.model_hint, True)

    arp = _read_arp_table()
    for ip, mac in arp.items():
        if not mac:
            continue
        if not _ip_in_any_cidr(ip, cidrs):
            continue
        if ip not in discovered:
            discovered[ip] = ("arp-neighbor", None, True)

    now = datetime.now(timezone.utc)
    updated = 0

    with Session(engine) as session:
        for ip, (adapter_name, model_hint, reachable) in discovered.items():
            mac = arp.get(ip)

            device = None
            if mac:
                device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_mac == mac)).first()
            if not device:
                device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == ip)).first()
            if not device:
                device = DeviceRuntime(device_ip=ip)

            device.device_ip = ip
            if mac:
                device.device_mac = mac
            device.probe_reachable = reachable
            if adapter_name:
                device.detected_adapter = adapter_name
            if model_hint:
                device.detected_model = model_hint
            if device.status == "OFF":
                device.status = "ON"
            device.last_heartbeat_at = now

            binding = None
            if mac:
                binding = session.exec(select(PrinterBinding).where(PrinterBinding.printer_mac == mac)).first()
                if binding:
                    # Keep printer routing usable when DHCP changes IP.
                    binding.printer_ip = ip
                    device.is_bound = True
                    device.bound_printer_id = binding.printer_id

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

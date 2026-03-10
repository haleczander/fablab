from __future__ import annotations

import ipaddress
import logging
import socket
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

from orchestrator.domain.models import MacAddress

logger = logging.getLogger(__name__)


class ScapyArpNeighborScanner:
    def scan(self, network: str, subnet_mask: str, timeout_s: float) -> dict[str, str]:
        target_network = self._to_network(network, subnet_mask)
        if not target_network:
            return {}

        table = self._scan_with_nmap(target_network, timeout_s)
        if not table:
            self._prime_arp_cache(target_network, timeout_s)
        table.update(self._read_arp_cache(target_network))
        return table

    def _scan_with_nmap(
        self,
        target_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        timeout_s: float,
    ) -> dict[str, str]:
        cmd = ["nmap", "-n", "-Pn", "-p", "80", "--open", str(target_network), "-oX", "-"]
        scan_timeout = max(10.0, min(60.0, timeout_s * 40.0))
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=scan_timeout,
                check=False,
            )
        except FileNotFoundError:
            logger.warning("discovery: nmap not found in container, ARP scan via nmap skipped")
            return {}
        except PermissionError:
            logger.warning("discovery: nmap permission denied, ARP scan via nmap skipped")
            return {}
        except subprocess.TimeoutExpired:
            logger.warning("discovery: nmap timed out for %s", target_network)
            return {}
        except OSError as exc:
            logger.warning("discovery: nmap OS error for %s: %s", target_network, exc)
            return {}

        if completed.returncode != 0:
            logger.warning(
                "discovery: nmap returned code %s for %s (stderr=%s)",
                completed.returncode,
                target_network,
                (completed.stderr or "").strip(),
            )
            return {}

        try:
            root = ET.fromstring(completed.stdout)
        except ET.ParseError:
            logger.warning("discovery: nmap XML parse error for %s", target_network)
            return {}

        table: dict[str, str] = {}
        for host in root.findall("host"):
            status = host.find("status")
            if status is not None and status.get("state") != "up":
                continue

            ip: str | None = None
            mac: str | None = None
            for address in host.findall("address"):
                addr = (address.get("addr") or "").strip()
                addr_type = (address.get("addrtype") or "").strip().lower()
                if not addr:
                    continue
                if addr_type in {"ipv4", "ipv6"} and not ip:
                    ip = addr
                if addr_type == "mac":
                    parsed = MacAddress.parse(addr)
                    mac = str(parsed) if parsed else None
            if ip:
                table[ip] = mac or ""
        return table

    @staticmethod
    def _read_arp_cache(
        target_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    ) -> dict[str, str]:
        if target_network.version != 4:
            return {}

        try:
            with open("/proc/net/arp", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError:
            return {}

        table: dict[str, str] = {}
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue

            ip = (parts[0] or "").strip()
            mac = MacAddress.parse(parts[3])
            if not ip or not mac:
                continue

            try:
                if ipaddress.ip_address(ip) in target_network:
                    table[ip] = str(mac)
            except ValueError:
                continue
        return table

    @staticmethod
    def _prime_arp_cache(
        target_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        timeout_s: float,
    ) -> None:
        if target_network.version != 4:
            return

        hosts = [str(host) for host in target_network.hosts()]
        if not hosts:
            return

        connect_timeout = max(0.05, min(0.5, timeout_s))

        def _touch_host(ip: str) -> None:
            try:
                with socket.create_connection((ip, 80), timeout=connect_timeout):
                    return
            except OSError:
                return

        with ThreadPoolExecutor(max_workers=min(64, len(hosts))) as pool:
            for future in [pool.submit(_touch_host, ip) for ip in hosts]:
                try:
                    future.result()
                except Exception:
                    continue

    @staticmethod
    def _to_network(network: str, subnet_mask: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
        net_raw = str(network or "").strip()
        mask_raw = str(subnet_mask or "").strip()
        if not net_raw or not mask_raw:
            return None
        if mask_raw.startswith("/"):
            mask_raw = mask_raw[1:]
        try:
            return ipaddress.ip_network(f"{net_raw}/{mask_raw}", strict=False)
        except ValueError:
            return None

from __future__ import annotations

import ipaddress
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from orchestrator.domain.mac import normalize_mac


class ScapyArpNeighborScanner:
    def scan(self, network: str, subnet_mask: str, timeout_s: float) -> dict[str, str]:
        target_network = self._to_network(network, subnet_mask)
        if not target_network:
            return {}

        nmap_table = self._scan_with_nmap(target_network, timeout_s)
        if nmap_table is not None:
            return nmap_table

        return self._scan_with_scapy(target_network, timeout_s)

    def _scan_with_nmap(
        self,
        target_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        timeout_s: float,
    ) -> dict[str, str] | None:
        cmd = ["nmap", "-sn", "-n", "-PR", str(target_network), "-oX", "-"]
        scan_timeout = max(5.0, min(60.0, timeout_s * 10.0))
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=scan_timeout,
                check=False,
            )
        except (FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired):
            return None

        if completed.returncode != 0:
            return None

        try:
            root = ET.fromstring(completed.stdout)
        except ET.ParseError:
            return None

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
                    mac = normalize_mac(addr)
            if ip and mac:
                table[ip] = mac
        return table

    def _scan_with_scapy(
        self,
        target_network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        timeout_s: float,
    ) -> dict[str, str]:
        try:
            from scapy.all import ARP, Ether, conf, srp  # type: ignore
        except Exception:
            return {}

        table: dict[str, str] = {}
        bounded_timeout = max(0.3, min(timeout_s, 2.5))
        iface = self._resolve_iface_for_network(conf, target_network)
        try:
            request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=str(target_network))
            answered, _ = srp(
                request,
                timeout=bounded_timeout,
                retry=0,
                verbose=False,
                iface=iface,
            )
        except Exception:
            return {}

        for _, response in answered:
            ip = str(getattr(response, "psrc", "")).strip()
            mac = normalize_mac(getattr(response, "hwsrc", None))
            if ip and mac:
                table[ip] = mac
        return table

    @staticmethod
    def _resolve_iface_for_network(conf: Any, network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> str | None:
        try:
            probe_ip = str(next(network.hosts())) if network.num_addresses > 2 else str(network.network_address)
            route = conf.route.route(probe_ip)
            iface = route[0] if isinstance(route, tuple) and route else None
            if iface:
                return str(iface)
        except Exception:
            return None
        return None

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

import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

from orchestrator.infrastructure.network_discovery.device_probers import ProbeResult, probe_device


def scan_cidr(cidr: str, timeout_s: float) -> list[tuple[str, ProbeResult]]:
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]
    results: list[tuple[str, ProbeResult]] = []
    with ThreadPoolExecutor(max_workers=min(24, len(hosts) or 1)) as executor:
        futures = {executor.submit(probe_device, ip, timeout_s): ip for ip in hosts}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                result = fut.result()
            except Exception:
                continue
            if result.reachable:
                results.append((ip, result))
    results.sort(key=lambda item: item[0])
    return results


import asyncio
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request

from orchestrator.api.dependencies import (
    get_binding_by_mac_use_case,
    get_binding_by_ip_use_case,
    get_binding_by_serial_use_case,
    get_device_runtime_repo,
    get_ingest_device_state_use_case,
    get_list_device_binding_rows_use_case,
    get_list_device_runtimes_use_case,
    get_list_fleet_use_case,
    get_list_unmatched_contract_devices_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
    get_pop_next_command_use_case,
)
from orchestrator.api.events import broadcast_devices, broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    DiscoverNetworkHostsUseCase,
    GetBindingByMacUseCase,
    GetBindingByIpUseCase,
    GetBindingBySerialUseCase,
    IngestDeviceStateUseCase,
    ListDeviceBindingRowsUseCase,
    ListDeviceRuntimesUseCase,
    ListFleetUseCase,
    ListUnmatchedContractDevicesUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    PopNextCommandUseCase,
)
from orchestrator.domain.models import DeviceRuntime
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.schemas import DeviceIgnoreByMacInput, DeviceIgnoreInput, DeviceIngestInput
from orchestrator.infrastructure.adapters import probe_device
from orchestrator.infrastructure.discovery_cache import build_rows_from_discovery, replace_snapshot
from orchestrator.infrastructure.scapy_arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.repositories import SqlModelDeviceRuntimeRepository
from config import ORCH_DISCOVERY_CIDRS, ORCH_DISCOVERY_MAX_HOSTS, ORCH_DISCOVERY_TIMEOUT_S

router = APIRouter(tags=["orchestrator"])


def _parse_cidrs(raw: str) -> list[str]:
    cidrs: list[str] = []
    for chunk in (raw or "").split(","):
        item = chunk.strip()
        if not item:
            continue
        ipaddress.ip_network(item, strict=False)
        cidrs.append(item)
    return cidrs


def _split_network_and_mask(cidr: str) -> tuple[str, str]:
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network.network_address), str(network.netmask)


@router.get("/devices", response_model=list[DeviceRuntime])
def list_devices(
    list_device_runtimes_use_case: ListDeviceRuntimesUseCase = Depends(get_list_device_runtimes_use_case),
) -> list[DeviceRuntime]:
    return list_device_runtimes_use_case.execute()


@router.post("/devices/state-ingest", response_model=DeviceRuntime)
async def ingest_device_state(
    payload: DeviceIngestInput,
    request: Request,
    ingest_device_state_use_case: IngestDeviceStateUseCase = Depends(get_ingest_device_state_use_case),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> DeviceRuntime:
    source_ip = request.client.host if request.client else "0.0.0.0"
    device, runtime, is_new_device = ingest_device_state_use_case.execute(source_ip, payload)
    await broadcast_events("device_updated", device.model_dump(mode="json"))
    if runtime:
        await broadcast_events("runtime_updated", runtime.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        },
    )
    if is_new_device:
        await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return device


@router.patch("/devices/{device_id}/ignored", response_model=DeviceRuntime)
async def set_device_ignored(
    device_id: int,
    payload: DeviceIgnoreInput,
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
) -> DeviceRuntime:
    row = device_runtime_repo.get_by_id(device_id)
    if not row:
        raise HTTPException(status_code=404, detail="device not found")
    row.is_ignored = payload.is_ignored
    updated = device_runtime_repo.save(row)
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    return updated


@router.post("/devices/ignored/by-mac", response_model=DeviceRuntime)
async def set_device_ignored_by_mac(
    payload: DeviceIgnoreByMacInput,
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
) -> DeviceRuntime:
    mac = normalize_mac(payload.device_mac)
    if not mac:
        raise HTTPException(status_code=400, detail="invalid device_mac")

    row = device_runtime_repo.get_by_mac(mac)
    if not row:
        if not payload.is_ignored:
            raise HTTPException(status_code=404, detail="device not found")
        row = DeviceRuntime(
            device_ip=str(payload.device_ip).strip(),
            device_mac=mac,
            device_serial=(payload.device_serial or "").strip() or None,
            detected_adapter=(payload.detected_adapter or "").strip() or None,
            detected_model=(payload.detected_model or "").strip() or None,
            probe_reachable=True,
        )

    row.is_ignored = payload.is_ignored
    updated = device_runtime_repo.save(row)
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    return updated


@router.get("/devices/commands/next")
def pop_next_command_for_source_ip(
    request: Request,
    binding_by_mac_use_case: GetBindingByMacUseCase = Depends(get_binding_by_mac_use_case),
    binding_by_ip_use_case: GetBindingByIpUseCase = Depends(get_binding_by_ip_use_case),
    binding_by_serial_use_case: GetBindingBySerialUseCase = Depends(get_binding_by_serial_use_case),
    pop_next_command_use_case: PopNextCommandUseCase = Depends(get_pop_next_command_use_case),
) -> dict[str, str | int] | None:
    source_ip = request.client.host if request.client else "0.0.0.0"
    source_mac = normalize_mac(request.headers.get("X-Printer-MAC"))
    source_serial = (request.headers.get("X-Printer-Serial") or "").strip() or None
    binding = binding_by_serial_use_case.execute(source_serial) if source_serial else None
    if not binding:
        binding = binding_by_mac_use_case.execute(source_mac) if source_mac else None
    if not binding:
        binding = binding_by_ip_use_case.execute(source_ip)
    if not binding:
        return None
    return pop_next_command_use_case.execute(binding.printer_id)


@router.get("/devices/contracts/unmatched")
def list_unmatched_contract_devices(
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
) -> list[dict[str, str | None]]:
    return list_unmatched_contract_devices_use_case.execute()


@router.post("/discovery/refresh")
async def refresh_network_discovery(
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> dict[str, int]:
    cidrs = _parse_cidrs(ORCH_DISCOVERY_CIDRS)
    discover_network_hosts = DiscoverNetworkHostsUseCase(
        arp_scanner=ScapyArpNeighborScanner(),
        probe_device_fn=probe_device,
    )

    merged_hosts: dict[str, tuple[str | None, str | None, str | None, bool]] = {}
    merged_arp: dict[str, str] = {}
    for cidr in cidrs:
        network, subnet_mask = _split_network_and_mask(cidr)
        discovery_result = await asyncio.to_thread(
            discover_network_hosts.execute,
            network=network,
            subnet_mask=subnet_mask,
            timeout_s=ORCH_DISCOVERY_TIMEOUT_S,
            max_hosts=ORCH_DISCOVERY_MAX_HOSTS,
        )
        merged_arp.update(discovery_result.arp_table)
        for ip, host in discovery_result.hosts.items():
            merged_hosts[ip] = (host.adapter_name, host.model_hint, host.serial_hint, host.reachable)

    replace_snapshot(build_rows_from_discovery(merged_hosts, merged_arp))
    updated = len(merged_hosts)
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return {"updated": int(updated)}

import asyncio
import ipaddress

from fastapi import APIRouter, Depends

from orchestrator.api import dependencies
from orchestrator.api.events import broadcast_devices, broadcast_machines
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    MachineStatesPayloadUseCase,
    RefreshNetworkDiscoveryUseCase,
)
from config import ORCH_DISCOVERY_CIDRS, ORCH_DISCOVERY_MAX_HOSTS, ORCH_DISCOVERY_TIMEOUT_S

router = APIRouter(prefix="/discovery", tags=["orchestrator"])


def _parse_cidrs(raw: str) -> list[str]:
    cidrs: list[str] = []
    for chunk in (raw or "").split(","):
        item = chunk.strip()
        if not item:
            continue
        ipaddress.ip_network(item, strict=False)
        cidrs.append(item)
    return cidrs


@router.post("/refresh")
async def refresh_network_discovery(
    refresh_network_discovery_use_case: RefreshNetworkDiscoveryUseCase = Depends(
        dependencies.dep(RefreshNetworkDiscoveryUseCase)
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
) -> dict[str, int]:
    cidrs = _parse_cidrs(ORCH_DISCOVERY_CIDRS)
    updated = await asyncio.to_thread(
        refresh_network_discovery_use_case.execute,
        cidrs=cidrs,
        timeout_s=ORCH_DISCOVERY_TIMEOUT_S,
        max_hosts=ORCH_DISCOVERY_MAX_HOSTS,
    )
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return {"updated": int(updated)}


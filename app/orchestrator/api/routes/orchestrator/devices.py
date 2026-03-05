from fastapi import APIRouter, Depends, Request

from app.orchestrator.api.dependencies import (
    get_binding_by_ip_use_case,
    get_ingest_device_state_use_case,
    get_list_fleet_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
    get_pop_next_command_use_case,
)
from app.orchestrator.api.events import broadcast_events, broadcast_machines
from app.orchestrator.application.use_cases import (
    GetBindingByIpUseCase,
    IngestDeviceStateUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    PopNextCommandUseCase,
)
from app.orchestrator.domain.models import DeviceRuntime
from app.orchestrator.domain.schemas import DeviceIngestInput

router = APIRouter(tags=["orchestrator"])


@router.post("/devices/state-ingest", response_model=DeviceRuntime)
async def ingest_device_state(
    payload: DeviceIngestInput,
    request: Request,
    ingest_device_state_use_case: IngestDeviceStateUseCase = Depends(get_ingest_device_state_use_case),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> DeviceRuntime:
    source_ip = request.client.host if request.client else "0.0.0.0"
    device, runtime = ingest_device_state_use_case.execute(source_ip, payload)
    await broadcast_events("device_updated", device.model_dump(mode="json"))
    if runtime:
        await broadcast_events("runtime_updated", runtime.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
        },
    )
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return device


@router.get("/devices/commands/next")
def pop_next_command_for_source_ip(
    request: Request,
    binding_by_ip_use_case: GetBindingByIpUseCase = Depends(get_binding_by_ip_use_case),
    pop_next_command_use_case: PopNextCommandUseCase = Depends(get_pop_next_command_use_case),
) -> dict[str, str | int] | None:
    source_ip = request.client.host if request.client else "0.0.0.0"
    binding = binding_by_ip_use_case.execute(source_ip)
    if not binding:
        return None
    return pop_next_command_use_case.execute(binding.printer_id)

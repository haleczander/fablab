from fastapi import APIRouter, Depends, HTTPException, Request

from orchestrator.api import dependencies
from orchestrator.api.events import broadcast_devices, broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    GetBindingByIpUseCase,
    GetBindingByMacUseCase,
    GetBindingBySerialUseCase,
    IngestDeviceStateUseCase,
    ListDeviceBindingRowsUseCase,
    ListDeviceRuntimesUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
    PopNextCommandUseCase,
    SetDeviceIgnoredByMacUseCase,
    SetDeviceIgnoredUseCase,
)
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import DeviceRuntime, PrinterBinding
from orchestrator.domain.schemas import DeviceIgnoreByMacInput, DeviceIgnoreInput, DeviceIngestInput

router = APIRouter(prefix="/devices", tags=["orchestrator"])


@router.get("", response_model=list[DeviceRuntime])
def list_devices(
    list_device_runtimes_use_case: ListDeviceRuntimesUseCase = Depends(dependencies.dep(ListDeviceRuntimesUseCase)),
) -> list[DeviceRuntime]:
    return list_device_runtimes_use_case.execute()


@router.post("/state-ingest", response_model=DeviceRuntime)
async def ingest_device_state(
    payload: DeviceIngestInput,
    request: Request,
    ingest_device_state_use_case: IngestDeviceStateUseCase = Depends(dependencies.dep(IngestDeviceStateUseCase)),
    list_fleet_use_case: ListFleetUseCase = Depends(dependencies.dep(ListFleetUseCase)),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(dependencies.dep(ListUnboundIpsUseCase)),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
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


@router.patch("/{device_id}/ignored", response_model=PrinterBinding)
async def set_device_ignored(
    device_id: int,
    payload: DeviceIgnoreInput,
    set_device_ignored_use_case: SetDeviceIgnoredUseCase = Depends(dependencies.dep(SetDeviceIgnoredUseCase)),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
) -> PrinterBinding:
    try:
        updated = set_device_ignored_use_case.execute(device_id=device_id, is_ignored=payload.is_ignored)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    return updated


@router.post("/ignored/by-mac", response_model=PrinterBinding)
async def set_device_ignored_by_mac(
    payload: DeviceIgnoreByMacInput,
    set_device_ignored_by_mac_use_case: SetDeviceIgnoredByMacUseCase = Depends(
        dependencies.dep(SetDeviceIgnoredByMacUseCase)
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
) -> PrinterBinding:
    try:
        updated = set_device_ignored_by_mac_use_case.execute(
            device_mac=payload.device_mac,
            device_ip=str(payload.device_ip).strip(),
            is_ignored=payload.is_ignored,
            device_serial=(payload.device_serial or "").strip() or None,
            detected_adapter=(payload.detected_adapter or "").strip() or None,
            detected_model=(payload.detected_model or "").strip() or None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    return updated


@router.get("/commands/next")
def pop_next_command_for_source_ip(
    request: Request,
    binding_by_mac_use_case: GetBindingByMacUseCase = Depends(dependencies.dep(GetBindingByMacUseCase)),
    binding_by_ip_use_case: GetBindingByIpUseCase = Depends(dependencies.dep(GetBindingByIpUseCase)),
    binding_by_serial_use_case: GetBindingBySerialUseCase = Depends(dependencies.dep(GetBindingBySerialUseCase)),
    pop_next_command_use_case: PopNextCommandUseCase = Depends(dependencies.dep(PopNextCommandUseCase)),
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


@router.get("/contracts/unmatched")
def list_unmatched_contract_devices(
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
) -> list[dict[str, str | None]]:
    return list_unmatched_contract_devices_use_case.execute()

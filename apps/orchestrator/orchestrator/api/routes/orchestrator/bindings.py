from fastapi import APIRouter, Depends, HTTPException, Response

from orchestrator.api.dependencies import (
    get_binding_repo,
    get_device_runtime_repo,
    get_list_device_binding_rows_use_case,
    get_list_fleet_use_case,
    get_list_unmatched_contract_devices_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
    get_upsert_binding_use_case,
)
from orchestrator.api.events import broadcast_devices, broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnmatchedContractDevicesUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    UpsertBindingUseCase,
)
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.schemas import BindPrinterInput
from orchestrator.infrastructure.repositories import SqlModelDeviceRuntimeRepository, SqlModelPrinterBindingRepository

router = APIRouter(tags=["orchestrator"])


@router.post("/printer-bindings", response_model=PrinterBinding)
async def bind_printer(
    payload: BindPrinterInput,
    upsert_binding_use_case: UpsertBindingUseCase = Depends(get_upsert_binding_use_case),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> PrinterBinding:
    row = upsert_binding_use_case.execute(
        printer_id=payload.printer_id,
        printer_ip=(payload.printer_ip or "").strip() or None,
        printer_mac=normalize_mac(payload.printer_mac),
        printer_serial=(payload.printer_serial or "").strip() or None,
        printer_model=payload.printer_model,
        adapter_name=(payload.adapter_name or "").strip().lower() or None,
    )
    await broadcast_events("binding_updated", row.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        },
    )
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return row


@router.delete("/printer-bindings/{printer_id}", status_code=204)
async def unbind_printer(
    printer_id: str,
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> Response:
    row = binding_repo.get_by_printer_id(printer_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"binding introuvable pour {printer_id}")

    old_ip = row.printer_ip
    old_mac = row.printer_mac
    old_serial = row.printer_serial
    binding_repo.delete(row)

    device = None
    if old_serial:
        device = device_runtime_repo.get_by_serial(old_serial)
    if not device and old_mac:
        device = device_runtime_repo.get_by_mac(old_mac)
    if not device and old_ip:
        device = device_runtime_repo.get_by_ip(old_ip)
    if device:
        device.is_bound = False
        device.bound_printer_id = None
        device_runtime_repo.save(device)

    await broadcast_events("binding_deleted", {"printer_id": printer_id})
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        },
    )
    await broadcast_devices("devices_snapshot", list_device_binding_rows_use_case.execute())
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return Response(status_code=204)


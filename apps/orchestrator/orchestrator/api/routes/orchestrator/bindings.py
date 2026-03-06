from fastapi import APIRouter, Depends, HTTPException, Response

from orchestrator.api import dependencies
from orchestrator.api.events import broadcast_devices, broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
    UnbindPrinterUseCase,
    UpsertBindingUseCase,
)
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.schemas import BindPrinterInput

router = APIRouter(prefix="/printer-bindings", tags=["orchestrator"])


@router.post("", response_model=PrinterBinding)
async def bind_printer(
    payload: BindPrinterInput,
    upsert_binding_use_case: UpsertBindingUseCase = Depends(dependencies.dep(UpsertBindingUseCase)),
    list_fleet_use_case: ListFleetUseCase = Depends(dependencies.dep(ListFleetUseCase)),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(dependencies.dep(ListUnboundIpsUseCase)),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
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


@router.delete("/{printer_id}", status_code=204)
async def unbind_printer(
    printer_id: str,
    unbind_printer_use_case: UnbindPrinterUseCase = Depends(dependencies.dep(UnbindPrinterUseCase)),
    list_fleet_use_case: ListFleetUseCase = Depends(dependencies.dep(ListFleetUseCase)),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(dependencies.dep(ListUnboundIpsUseCase)),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
) -> Response:
    try:
        unbind_printer_use_case.execute(printer_id=printer_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

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


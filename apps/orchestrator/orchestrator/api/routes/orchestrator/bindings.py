from fastapi import APIRouter, Depends

from orchestrator.api.dependencies import (
    get_list_fleet_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
    get_upsert_binding_use_case,
)
from orchestrator.api.events import broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    UpsertBindingUseCase,
)
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import PrinterBinding
from orchestrator.domain.schemas import BindPrinterInput

router = APIRouter(tags=["orchestrator"])


@router.post("/printer-bindings", response_model=PrinterBinding)
async def bind_printer(
    payload: BindPrinterInput,
    upsert_binding_use_case: UpsertBindingUseCase = Depends(get_upsert_binding_use_case),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> PrinterBinding:
    row = upsert_binding_use_case.execute(
        printer_id=payload.printer_id,
        printer_ip=str(payload.printer_ip) if payload.printer_ip is not None else None,
        printer_mac=normalize_mac(payload.printer_mac),
        printer_model=payload.printer_model,
    )
    await broadcast_events("binding_updated", row.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
        },
    )
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return row


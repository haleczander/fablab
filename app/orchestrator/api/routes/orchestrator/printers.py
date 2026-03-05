from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.orchestrator.api.dependencies import (
    get_binding_by_printer_id_use_case,
    get_enqueue_start_command_use_case,
    get_list_fleet_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
    get_mark_job_sent_use_case,
)
from app.orchestrator.api.events import broadcast_events, broadcast_machines
from app.orchestrator.application.use_cases import (
    EnqueueStartPrintCommandUseCase,
    GetBindingByPrinterIdUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    MarkJobSentUseCase,
)
from app.orchestrator.domain.schemas import StartPrintCommandInput

router = APIRouter(tags=["orchestrator"])


@router.post("/printers/{printer_id}/commands/start")
async def command_start_print(
    printer_id: str,
    payload: StartPrintCommandInput,
    binding_by_printer_use_case: GetBindingByPrinterIdUseCase = Depends(get_binding_by_printer_id_use_case),
    enqueue_start_command_use_case: EnqueueStartPrintCommandUseCase = Depends(get_enqueue_start_command_use_case),
    mark_job_sent_use_case: MarkJobSentUseCase = Depends(get_mark_job_sent_use_case),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> dict[str, str | int]:
    binding = binding_by_printer_use_case.execute(printer_id)
    if not binding:
        raise HTTPException(status_code=404, detail=f"printer_id inconnu/non bind: {printer_id}")

    job_id = payload.job_id or f"JOB-AUTO-{uuid4().hex[:10].upper()}"
    command = {"type": "START_PRINT", "job_id": job_id, "est_duration_s": payload.est_duration_s}
    queued = enqueue_start_command_use_case.execute(printer_id, command)
    runtime = mark_job_sent_use_case.execute(printer_id=printer_id, job_id=job_id)

    out: dict[str, str | int] = {"printer_id": printer_id, "queued": queued, **command}
    await broadcast_events("command_queued", out)
    await broadcast_events("runtime_updated", runtime.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
        },
    )
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return out

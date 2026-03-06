from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from orchestrator.api import dependencies
from orchestrator.api.events import broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    CreatePrinterJobUseCase,
    EnqueueStartPrintCommandUseCase,
    GetBindingByPrinterIdUseCase,
    GetPrinterMachineInfoUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
    SyncPrinterStateUseCase,
)
from orchestrator.domain.models import PrinterRuntime
from orchestrator.domain.schemas import StartPrintCommandInput

router = APIRouter(prefix="/printers", tags=["orchestrator"])


@router.post("/{printer_id}/commands/start")
async def command_start_print(
    printer_id: str,
    payload: StartPrintCommandInput,
    binding_by_printer_use_case: GetBindingByPrinterIdUseCase = Depends(dependencies.dep(GetBindingByPrinterIdUseCase)),
    enqueue_start_command_use_case: EnqueueStartPrintCommandUseCase = Depends(
        dependencies.dep(EnqueueStartPrintCommandUseCase)
    ),
    create_printer_job_use_case: CreatePrinterJobUseCase = Depends(dependencies.dep(CreatePrinterJobUseCase)),
    list_fleet_use_case: ListFleetUseCase = Depends(dependencies.dep(ListFleetUseCase)),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(dependencies.dep(ListUnboundIpsUseCase)),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
) -> dict[str, str | int]:
    binding = binding_by_printer_use_case.execute(printer_id)
    if not binding:
        raise HTTPException(status_code=404, detail=f"printer_id inconnu/non bind: {printer_id}")

    job_id = payload.job_id or f"JOB-AUTO-{uuid4().hex[:10].upper()}"
    command = {"type": "START_PRINT", "job_id": job_id, "est_duration_s": payload.est_duration_s}
    queued = 0
    if (binding.adapter_name or "").lower() == "prusalink":
        printer_file_path = payload.printer_file_path or f"/local/{job_id}.gcode"
        try:
            remote = create_printer_job_use_case.execute(printer_id=printer_id, printer_file_path=printer_file_path)
        except (LookupError, ValueError) as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except RuntimeError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err
        command["remote_adapter"] = remote.get("adapter_name") or "prusalink"
        if remote.get("external_job_id"):
            command["external_job_id"] = str(remote["external_job_id"])
    else:
        queued = enqueue_start_command_use_case.execute(printer_id, command)

    out: dict[str, str | int] = {"printer_id": printer_id, "queued": queued, **command}
    await broadcast_events("command_queued", out)
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        },
    )
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return out


@router.get("/{printer_id}/machine-info")
def get_machine_info(
    printer_id: str,
    machine_info_use_case: GetPrinterMachineInfoUseCase = Depends(dependencies.dep(GetPrinterMachineInfoUseCase)),
) -> dict:
    try:
        return machine_info_use_case.execute(printer_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err


@router.post("/{printer_id}/state/sync", response_model=PrinterRuntime)
async def sync_machine_state(
    printer_id: str,
    sync_state_use_case: SyncPrinterStateUseCase = Depends(dependencies.dep(SyncPrinterStateUseCase)),
    list_fleet_use_case: ListFleetUseCase = Depends(dependencies.dep(ListFleetUseCase)),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(dependencies.dep(ListUnboundIpsUseCase)),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        dependencies.dep(ListUnmatchedContractDevicesUseCase)
    ),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(dependencies.dep(MachineStatesPayloadUseCase)),
) -> PrinterRuntime:
    try:
        runtime = sync_state_use_case.execute(printer_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err

    await broadcast_events("runtime_updated", runtime.model_dump(mode="json"))
    await broadcast_events(
        "fleet_updated",
        {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        },
    )
    await broadcast_machines("machines_updated", machine_states_use_case.execute())
    return runtime


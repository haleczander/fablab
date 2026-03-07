from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from orchestrator.api import dependencies
from orchestrator.api.schemas import StartPrintCommandInput
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import (
    CreatePrinterJobUseCase,
    EnqueueStartPrintCommandUseCase,
    GetBindingByPrinterIdUseCase,
)

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
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> dict[str, str | int]:
    try:
        binding = binding_by_printer_use_case.execute(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")

        job_id = payload.job_id or f"JOB-AUTO-{uuid4().hex[:10].upper()}"
        command = {"type": "START_PRINT", "job_id": job_id, "est_duration_s": payload.est_duration_s}
        queued = 0
        printer_file_path = payload.printer_file_path or f"/local/{job_id}.gcode"
        try:
            remote = create_printer_job_use_case.execute(printer_id=printer_id, printer_file_path=printer_file_path)
            command["remote_adapter"] = remote.get("adapter_name") or "prusalink"
            if remote.get("external_job_id"):
                command["external_job_id"] = str(remote["external_job_id"])
        except ValueError as err:
            if "adapter non supporte" in str(err):
                queued = enqueue_start_command_use_case.execute(printer_id, command)
            else:
                raise
        if "remote_adapter" not in command and queued == 0:
            queued = enqueue_start_command_use_case.execute(printer_id, command)
        out: dict[str, str | int] = {"printer_id": printer_id, "queued": queued, **command}
        await notifications.notify_command_queued(out)
        return out
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err


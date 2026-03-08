from uuid import uuid4

from orchestrator.application.app_services.orchestrator_notification_service import OrchestratorNotificationService
from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases.create_printer_job import CreatePrinterJobUseCase
from orchestrator.application.use_cases.enqueue_start_print_command import EnqueueStartPrintCommandUseCase
from orchestrator.application.use_cases.get_binding_by_printer_id import GetBindingByPrinterIdUseCase


class StartPrintCommandUseCase:
    binding_by_printer_use_case: GetBindingByPrinterIdUseCase = autowired()
    enqueue_start_command_use_case: EnqueueStartPrintCommandUseCase = autowired()
    create_printer_job_use_case: CreatePrinterJobUseCase = autowired()
    notifications: OrchestratorNotificationService = autowired()

    async def execute(
        self,
        printer_id: str,
        printer_file_path: str | None,
        job_id: str | None,
        est_duration_s: int,
    ) -> dict[str, str | int]:
        binding = self.binding_by_printer_use_case.execute(printer_id)
        if not binding:
            raise LookupError(f"printer_id inconnu/non bind: {printer_id}")

        resolved_job_id = job_id or f"JOB-AUTO-{uuid4().hex[:10].upper()}"
        command: dict[str, str | int] = {
            "type": "START_PRINT",
            "job_id": resolved_job_id,
            "est_duration_s": est_duration_s,
        }
        queued = 0
        resolved_printer_file_path = printer_file_path or f"/local/{resolved_job_id}.gcode"
        try:
            remote = self.create_printer_job_use_case.execute(
                printer_id=printer_id,
                printer_file_path=resolved_printer_file_path,
            )
            command["remote_adapter"] = remote.get("adapter_name") or "prusalink"
            if remote.get("external_job_id"):
                command["external_job_id"] = str(remote["external_job_id"])
        except ValueError as err:
            if "adapter non supporte" in str(err):
                queued = self.enqueue_start_command_use_case.execute(printer_id, command)
            else:
                raise
        if "remote_adapter" not in command and queued == 0:
            queued = self.enqueue_start_command_use_case.execute(printer_id, command)
        out: dict[str, str | int] = {"printer_id": printer_id, "queued": queued, **command}
        await self.notifications.notify_command_queued(out)
        return out

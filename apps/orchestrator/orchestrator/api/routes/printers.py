from fastapi import APIRouter, HTTPException

from orchestrator.api.schemas import StartPrintCommandInput
from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases import StartPrintCommandUseCase

router = APIRouter(prefix="/printers", tags=["orchestrator"])


class PrintersController:
    start_print_command_use_case: StartPrintCommandUseCase = autowired()

    async def command_start_print(
        self,
        printer_id: str,
        payload: StartPrintCommandInput,
    ) -> dict[str, str | int]:
        try:
            return await self.start_print_command_use_case.execute(
                printer_id=printer_id,
                printer_file_path=payload.printer_file_path,
                job_id=payload.job_id,
                est_duration_s=payload.est_duration_s,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except LookupError as err:
            raise HTTPException(status_code=404, detail=str(err)) from err
        except RuntimeError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err


controller = PrintersController()
router.add_api_route("/{printer_id}/commands/start", controller.command_start_print, methods=["POST"])


from fastapi import APIRouter, Depends, HTTPException, Response

from orchestrator.api import dependencies
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    UnbindPrinterUseCase,
    UpsertBindingUseCase,
)
from orchestrator.api.schemas import BindPrinterInput
from orchestrator.domain.models import MacAddress, PrinterBinding

router = APIRouter(prefix="/printer-bindings", tags=["orchestrator"])


@router.get("")
def list_printer_bindings(
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(dependencies.dep(ListDeviceBindingRowsUseCase)),
) -> list[dict[str, str | bool | int | None]]:
    return list_device_binding_rows_use_case.execute(include_ignored=True)


@router.post("", response_model=PrinterBinding)
async def bind_printer(
    payload: BindPrinterInput,
    upsert_binding_use_case: UpsertBindingUseCase = Depends(dependencies.dep(UpsertBindingUseCase)),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> PrinterBinding:
    row = upsert_binding_use_case.execute(
        printer_id=payload.printer_id,
        printer_ip=(payload.printer_ip or "").strip() or None,
        printer_mac=str(MacAddress.parse(payload.printer_mac)),
        printer_serial=(payload.printer_serial or "").strip() or None,
        printer_model=payload.printer_model,
        adapter_name=(payload.adapter_name or "").strip().lower() or None,
    )
    await notifications.notify_binding_updated(row)
    return row


@router.delete("/{printer_id}", status_code=204)
async def unbind_printer(
    printer_id: str,
    unbind_printer_use_case: UnbindPrinterUseCase = Depends(dependencies.dep(UnbindPrinterUseCase)),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> Response:
    try:
        unbind_printer_use_case.execute(printer_id=printer_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await notifications.notify_binding_deleted(printer_id)
    return Response(status_code=204)


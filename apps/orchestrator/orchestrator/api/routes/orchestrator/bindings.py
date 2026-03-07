from fastapi import APIRouter, Depends, HTTPException, Response

from orchestrator.api import dependencies
from orchestrator.api.schemas import BindingInput
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import ListBindingsUseCase, UnbindPrinterUseCase, UpsertBindingUseCase
from orchestrator.domain.models import MacAddress, PrinterBinding

router = APIRouter(prefix="/bindings", tags=["orchestrator"])


@router.get("")
def list_bindings(
    list_bindings_use_case: ListBindingsUseCase = Depends(dependencies.dep(ListBindingsUseCase)),
) -> list[dict[str, str | bool | int | None]]:
    return list_bindings_use_case.execute(include_ignored=True)


def _binding_kwargs(payload: BindingInput) -> dict[str, str | bool | None]:
    return {
        "printer_id": (payload.printer_id or "").strip() or None,
        "printer_ip": (payload.printer_ip or "").strip() or None,
        "printer_mac": str(MacAddress.parse(payload.printer_mac)),
        "printer_model": (payload.printer_model or "").strip() or None,
        "adapter_name": (payload.adapter_name or "").strip().lower() or None,
        "is_ignored": payload.is_ignored,
    }


@router.put("/{device_mac}", response_model=PrinterBinding)
async def upsert_binding(
    device_mac: str,
    payload: BindingInput,
    upsert_binding_use_case: UpsertBindingUseCase = Depends(dependencies.dep(UpsertBindingUseCase)),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> PrinterBinding:
    try:
        parsed_mac = MacAddress.parse(device_mac)
        if not parsed_mac:
            raise ValueError("device_mac invalide")
        body_mac = MacAddress.parse(payload.printer_mac)
        if body_mac and body_mac != parsed_mac:
            raise ValueError("device_mac URL et payload differents")
        kwargs = _binding_kwargs(payload)
        kwargs["printer_mac"] = str(parsed_mac)
        row = upsert_binding_use_case.execute(**kwargs)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    await notifications.notify_binding_updated(row)
    return row


@router.delete("/{device_mac}", status_code=204)
async def unbind_printer(
    device_mac: str,
    unbind_printer_use_case: UnbindPrinterUseCase = Depends(dependencies.dep(UnbindPrinterUseCase)),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> Response:
    try:
        parsed_mac = MacAddress.parse(device_mac)
        if not parsed_mac:
            raise ValueError("device_mac invalide")
        unbind_printer_use_case.execute(printer_mac=str(parsed_mac))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await notifications.notify_binding_deleted(str(parsed_mac))
    return Response(status_code=204)


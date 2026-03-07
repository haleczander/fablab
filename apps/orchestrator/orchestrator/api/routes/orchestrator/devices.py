from fastapi import APIRouter, Depends, HTTPException

from orchestrator.api import dependencies
from orchestrator.api.schemas import DeviceIgnoreByMacInput, DeviceIgnoreInput
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import (
    ListDeviceRuntimesUseCase,
    SetDeviceIgnoredByMacUseCase,
    SetDeviceIgnoredUseCase,
)
from orchestrator.domain.models import PrinterBinding

router = APIRouter(prefix="/devices", tags=["orchestrator"])


@router.get("")
def list_devices(
    list_device_runtimes_use_case: ListDeviceRuntimesUseCase = Depends(dependencies.dep(ListDeviceRuntimesUseCase)),
) -> list[dict[str, str | bool | float | None]]:
    return list_device_runtimes_use_case.execute()


@router.patch("/{device_id}/ignored", response_model=PrinterBinding)
async def set_device_ignored(
    device_id: int,
    payload: DeviceIgnoreInput,
    set_device_ignored_use_case: SetDeviceIgnoredUseCase = Depends(dependencies.dep(SetDeviceIgnoredUseCase)),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> PrinterBinding:
    try:
        updated = set_device_ignored_use_case.execute(device_id=device_id, is_ignored=payload.is_ignored)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await notifications.notify_devices_changed()
    return updated


@router.post("/ignored/by-mac", response_model=PrinterBinding)
async def set_device_ignored_by_mac(
    payload: DeviceIgnoreByMacInput,
    set_device_ignored_by_mac_use_case: SetDeviceIgnoredByMacUseCase = Depends(
        dependencies.dep(SetDeviceIgnoredByMacUseCase)
    ),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> PrinterBinding:
    try:
        updated = set_device_ignored_by_mac_use_case.execute(
            device_mac=payload.device_mac,
            device_ip=str(payload.device_ip).strip(),
            is_ignored=payload.is_ignored,
            device_serial=(payload.device_serial or "").strip() or None,
            detected_adapter=(payload.detected_adapter or "").strip() or None,
            detected_model=(payload.detected_model or "").strip() or None,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await notifications.notify_devices_changed()
    return updated

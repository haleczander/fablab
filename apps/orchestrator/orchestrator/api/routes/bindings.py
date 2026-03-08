from fastapi import APIRouter, HTTPException, Response

from orchestrator.api.schemas import BindingInput
from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases import ListBindingsUseCase, UnbindPrinterUseCase, UpsertBindingUseCase
from orchestrator.domain.models import MacAddress, PrinterBinding

router = APIRouter(prefix="/bindings", tags=["orchestrator"])

def _binding_kwargs(payload: BindingInput) -> dict[str, str | bool | None]:
    return {
        "printer_id": (payload.printer_id or "").strip() or None,
        "printer_ip": (payload.printer_ip or "").strip() or None,
        "printer_mac": str(MacAddress.parse(payload.printer_mac)),
        "printer_model": (payload.printer_model or "").strip() or None,
        "adapter_name": (payload.adapter_name or "").strip().lower() or None,
        "is_ignored": payload.is_ignored,
    }


class BindingsController:
    list_bindings_use_case: ListBindingsUseCase = autowired()
    upsert_binding_use_case: UpsertBindingUseCase = autowired()
    unbind_printer_use_case: UnbindPrinterUseCase = autowired()

    def list_bindings(self) -> list[dict[str, str | bool | int | None]]:
        return self.list_bindings_use_case.execute(include_ignored=True)

    async def upsert_binding(self, device_mac: str, payload: BindingInput) -> PrinterBinding:
        try:
            parsed_mac = MacAddress.parse(device_mac)
            if not parsed_mac:
                raise ValueError("device_mac invalide")
            body_mac = MacAddress.parse(payload.printer_mac)
            if body_mac and body_mac != parsed_mac:
                raise ValueError("device_mac URL et payload differents")
            kwargs = _binding_kwargs(payload)
            kwargs["printer_mac"] = str(parsed_mac)
            return await self.upsert_binding_use_case.execute(**kwargs)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

    async def unbind_printer(self, device_mac: str) -> Response:
        try:
            parsed_mac = MacAddress.parse(device_mac)
            if not parsed_mac:
                raise ValueError("device_mac invalide")
            await self.unbind_printer_use_case.execute(printer_mac=str(parsed_mac))
            return Response(status_code=204)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except LookupError as err:
            raise HTTPException(status_code=404, detail=str(err)) from err


controller = BindingsController()
router.add_api_route("", controller.list_bindings, methods=["GET"])
router.add_api_route("/{device_mac}", controller.upsert_binding, methods=["PUT"], response_model=PrinterBinding)
router.add_api_route("/{device_mac}", controller.unbind_printer, methods=["DELETE"], status_code=204)


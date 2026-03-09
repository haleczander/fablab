from orchestrator.application.app_services.orchestrator_notification_service import OrchestratorNotificationService
from orchestrator.application.dependencies import autowired
from orchestrator.application.ports import PrinterBindingPersistencePort


class UnbindPrinterUseCase:
    binding_repo: PrinterBindingPersistencePort = autowired()
    notifications: OrchestratorNotificationService = autowired()

    async def execute(self, printer_mac: str) -> None:
        row = self.binding_repo.get_by_mac(printer_mac)
        if not row:
            raise LookupError(f"binding introuvable pour {printer_mac}")

        self.binding_repo.delete(row)
        await self.notifications.notify_binding_deleted(printer_mac)

from app.orchestrator.application.ports import PrinterBindingRepositoryPort
from app.orchestrator.domain.models import PrinterBinding


class ListBindingsUseCase:
    def __init__(self, binding_repo: PrinterBindingRepositoryPort) -> None:
        self.binding_repo = binding_repo

    def execute(self) -> list[PrinterBinding]:
        return self.binding_repo.list_all()

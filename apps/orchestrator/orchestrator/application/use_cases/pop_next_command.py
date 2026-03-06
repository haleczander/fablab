from orchestrator.application.app_services import CommandQueueService


class PopNextCommandUseCase:
    def __init__(self, queue: CommandQueueService) -> None:
        self.queue = queue

    def execute(self, printer_id: str) -> dict[str, str | int] | None:
        return self.queue.pop(printer_id)


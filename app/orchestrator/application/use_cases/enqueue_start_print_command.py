from app.orchestrator.application.app_services import CommandQueueService


class EnqueueStartPrintCommandUseCase:
    def __init__(self, queue: CommandQueueService) -> None:
        self.queue = queue

    def execute(self, printer_id: str, command: dict[str, str | int]) -> int:
        return self.queue.push(printer_id, command)

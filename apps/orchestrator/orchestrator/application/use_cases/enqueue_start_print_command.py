from orchestrator.application.app_services import CommandQueueService


class EnqueueStartPrintCommandUseCase:
    def __init__(self, queue: CommandQueueService) -> None:
        self._queue = queue

    def execute(self, printer_id: str, command: dict[str, str | int]) -> int:
        return self._queue.push(printer_id, command)


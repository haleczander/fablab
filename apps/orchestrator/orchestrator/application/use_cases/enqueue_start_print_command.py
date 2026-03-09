from orchestrator.application.dependencies import autowired
from orchestrator.application.app_services.command_queue import CommandQueueService


class EnqueueStartPrintCommandUseCase:
    queue: CommandQueueService = autowired()

    def execute(self, printer_id: str, command: dict[str, str | int]) -> int:
        return self.queue.push(printer_id, command)


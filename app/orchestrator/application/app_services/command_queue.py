from collections import defaultdict, deque
from threading import Lock


class CommandQueueService:
    def __init__(self) -> None:
        self._queues: dict[str, deque[dict[str, str | int]]] = defaultdict(deque)
        self._lock = Lock()

    def push(self, printer_id: str, command: dict[str, str | int]) -> int:
        with self._lock:
            self._queues[printer_id].append(command)
            return len(self._queues[printer_id])

    def pop(self, printer_id: str) -> dict[str, str | int] | None:
        with self._lock:
            queue = self._queues[printer_id]
            if not queue:
                return None
            return queue.popleft()

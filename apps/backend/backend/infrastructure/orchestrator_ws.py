import asyncio
import json
from threading import Lock

from websockets import connect
from websockets.exceptions import WebSocketException

from config import ORCHESTRATOR_INTERNAL_URL, ORCHESTRATOR_WS_RETRY_S

_machine_states: dict[str, dict[str, str | None]] = {}
_state_lock = Lock()
_subscribers: set[asyncio.Queue[list[dict[str, str | None]]]] = set()
_subscribers_lock = Lock()
_MACHINE_KEYS = {
    "machine_id",
    "printer_id",
    "printer_ip",
    "printer_model",
    "last_heartbeat_at",
    "status",
    "model",
}


def _machines_ws_url() -> str:
    return ORCHESTRATOR_INTERNAL_URL.rstrip("/").replace("http://", "ws://").replace("https://", "wss://") + "/ws/machines"


def _save_snapshot(payload: list[dict[str, str | None]]) -> None:
    with _state_lock:
        _machine_states.clear()
        for row in payload:
            row = {k: row.get(k) for k in _MACHINE_KEYS}
            machine_id = row.get("machine_id")
            if machine_id:
                _machine_states[machine_id] = row


def _upsert_snapshot(payload: list[dict[str, str | None]]) -> None:
    with _state_lock:
        for row in payload:
            row = {k: row.get(k) for k in _MACHINE_KEYS}
            machine_id = row.get("machine_id")
            if machine_id:
                _machine_states[machine_id] = row


def get_machine_states() -> list[dict[str, str | None]]:
    with _state_lock:
        rows = list(_machine_states.values())
    rows.sort(key=lambda item: item["machine_id"] or "")
    return rows


def subscribe_machine_states() -> asyncio.Queue[list[dict[str, str | None]]]:
    queue: asyncio.Queue[list[dict[str, str | None]]] = asyncio.Queue(maxsize=1)
    with _subscribers_lock:
        _subscribers.add(queue)
    return queue


def unsubscribe_machine_states(queue: asyncio.Queue[list[dict[str, str | None]]]) -> None:
    with _subscribers_lock:
        _subscribers.discard(queue)


def _notify_subscribers() -> None:
    snapshot = get_machine_states()
    with _subscribers_lock:
        subscribers = list(_subscribers)
    for queue in subscribers:
        try:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(snapshot)
        except asyncio.QueueEmpty:
            pass
        except asyncio.QueueFull:
            pass


async def consume_machine_feed(stop_event: asyncio.Event) -> None:
    ws_url = _machines_ws_url()
    while not stop_event.is_set():
        try:
            async with connect(ws_url) as websocket:
                while not stop_event.is_set():
                    raw = await asyncio.wait_for(websocket.recv(), timeout=30)
                    message = json.loads(raw)
                    event = message.get("event")
                    payload = message.get("payload")
                    if event == "machines_snapshot" and isinstance(payload, list):
                        _save_snapshot(payload)
                        _notify_subscribers()
                    elif event == "machines_updated" and isinstance(payload, list):
                        _upsert_snapshot(payload)
                        _notify_subscribers()
        except (OSError, TimeoutError, WebSocketException, json.JSONDecodeError):
            await asyncio.sleep(ORCHESTRATOR_WS_RETRY_S)


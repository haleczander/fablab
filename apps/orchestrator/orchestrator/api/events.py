import json
from threading import Lock

from fastapi import WebSocket

ws_events_clients: set[WebSocket] = set()
ws_events_lock = Lock()
ws_machine_clients: set[WebSocket] = set()
ws_machine_lock = Lock()


async def broadcast_events(event: str, payload: dict | list | None = None) -> None:
    message = json.dumps({"event": event, "payload": payload})
    with ws_events_lock:
        clients = list(ws_events_clients)

    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.append(client)

    if dead:
        with ws_events_lock:
            for client in dead:
                ws_events_clients.discard(client)


async def broadcast_machines(event: str, payload: list[dict[str, str | None]]) -> None:
    message = json.dumps({"event": event, "payload": payload})
    with ws_machine_lock:
        clients = list(ws_machine_clients)

    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.append(client)

    if dead:
        with ws_machine_lock:
            for client in dead:
                ws_machine_clients.discard(client)


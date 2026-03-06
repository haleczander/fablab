import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.infrastructure.orchestrator_ws import subscribe_machine_states, unsubscribe_machine_states, get_machine_states

router = APIRouter(tags=["backend-api"])


@router.websocket("/ws/machines")
async def ws_machines(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = subscribe_machine_states()
    try:
        snapshot = get_machine_states()
        await websocket.send_text(json.dumps({"event": "machines_snapshot", "payload": snapshot}))
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            queue_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {receive_task, queue_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

            if queue_task in done:
                payload = queue_task.result()
                await websocket.send_text(json.dumps({"event": "machines_updated", "payload": payload}))

            if receive_task in done:
                message = receive_task.result()
                if message == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_machine_states(queue)


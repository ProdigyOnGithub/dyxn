from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):

        # document_id -> set(WebSocket)
        self.connections = defaultdict(set)

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()

        self.connections[document_id].add(websocket)

    def disconnect(self, websocket: WebSocket, document_id: str):
        self.connections[document_id].discard(websocket)

        if not self.connections[document_id]:
            del self.connections[document_id]

    async def broadcast(self, document_id: str, message: dict):
        dead = []

        for ws in self.connections.get(document_id, set()):

            try:

                await ws.send_json(message)

            except Exception:

                dead.append(ws)

        for ws in dead:

            self.disconnect(
                ws,
                document_id
            )


manager = ConnectionManager()
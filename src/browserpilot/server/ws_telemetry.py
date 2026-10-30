"""WebSocket telemetry hub for live viewport broadcasting and remote human takeover."""

import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("browserpilot.server.ws")


class TelemetryHub:
    """Manages active WebSocket connections and multiplexes telemetry and remote control events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Register and accept incoming WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister closed WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Transmit message payload to all active client connections."""
        async with self._lock:
            recipients = list(self.active_connections)

        payload = json.dumps(message)
        for ws in recipients:
            try:
                await ws.send_text(payload)
            except Exception as ex:
                logger.debug(f"Failed to transmit WebSocket message: {ex}")
                async with self._lock:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)


telemetry_hub = TelemetryHub()

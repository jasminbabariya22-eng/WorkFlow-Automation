"""
websocket.py
Thread-safe and async-safe WebSocket Connection Manager for Workflow Engine.
Broadcasts real-time workflow lifecycle events to ClientApp and Studio frontend.
"""

import asyncio
import json
import threading
from typing import List, Dict, Any, Optional
from fastapi import WebSocket
from app.core.logger import logger


class WorkflowConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
        self._lock = threading.Lock()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._main_loop = loop

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)
            if user_id:
                uid_str = str(user_id)
                if uid_str not in self.user_connections:
                    self.user_connections[uid_str] = []
                self.user_connections[uid_str].append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            for uid, conns in list(self.user_connections.items()):
                if websocket in conns:
                    conns.remove(websocket)
                if not conns:
                    self.user_connections.pop(uid, None)
        logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def _async_broadcast(self, payload: Dict[str, Any], target_user_id: Optional[str] = None):
        msg = json.dumps(payload, default=str)
        dead_connections = []

        with self._lock:
            if target_user_id and str(target_user_id) in self.user_connections:
                targets = list(self.user_connections[str(target_user_id)])
            else:
                targets = list(self.active_connections)

        for conn in targets:
            try:
                await conn.send_text(msg)
            except Exception as e:
                logger.warning(f"Error sending WebSocket message to client: {e}")
                dead_connections.append(conn)

        if dead_connections:
            with self._lock:
                for d in dead_connections:
                    self.disconnect(d)

    def broadcast_event(self, event_type: str, data: Dict[str, Any], target_user_id: Optional[str] = None):
        """
        Synchronous-friendly broadcast function that can be safely called from
        sync endpoints, background workers, or adapter methods.
        """
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": data.get("timestamp") or str(asyncio.get_event_loop().time() if self._main_loop else "")
        }

        # Try to schedule on running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = self._main_loop

        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_broadcast(payload, target_user_id), loop)
        else:
            # Fallback for worker threads
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._async_broadcast(payload, target_user_id))
                new_loop.close()

            t = threading.Thread(target=run_in_thread, daemon=True)
            t.start()


# Global Singleton
ws_manager = WorkflowConnectionManager()
